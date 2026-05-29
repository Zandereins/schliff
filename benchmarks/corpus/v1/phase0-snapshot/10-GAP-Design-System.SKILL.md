# ระบบรับรองแหล่งผลิต GAP พืช (Web Application)

## สารบัญ (Table of Contents)

1. [Tech Stack & Architecture](#1-tech-stack--architecture)
2. [โครงสร้างโปรเจกต์ (Project Structure)](#2-โครงสร้างโปรเจกต์-project-structure)
3. [Roles & Permissions](#3-roles--permissions)
4. [Authentication — SSO Flow](#4-authentication--sso-flow)
5. [Router Configuration](#5-router-configuration)
6. [Portal Page — หน้าเมนูระบบกลาพร้ง](#6-portal-page--หน้าเมนูระบบกลาง)
7. [Application Step Form (v-stepper)](#7-application-step-form-v-stepper)
8. [Dashboard](#8-dashboard)
9. [Application State Flow](#9-application-state-flow)
10. [Inspection Module](#10-inspection-module)
11. [Certificate Module](#11-certificate-module)
12. [Application Store (Pinia)](#12-application-store-pinia)
13. [Sidebar Navigation](#13-sidebar-navigation)
14. [Vuetify Theme Configuration](#14-vuetify-theme-configuration)
15. [API Endpoints Summary](#15-api-endpoints-summary)
16. [Environment Variables](#16-environment-variables)
17. [Deployment & DevOps Notes](#17-deployment--devops-notes)

---

## 1. Tech Stack & Architecture

|Layer             |Technology                                |
|------------------|------------------------------------------|
|Frontend Framework|Vue 3 (Composition API + `<script setup>`)|
|UI Library        |Vuetify 3                                 |
|Routing           |Vue Router 4                              |
|State Management  |Pinia                                     |
|Authentication    |SSO (OAuth 2.0 / OpenID Connect)          |
|HTTP Client       |Axios                                     |
|PDF Generation    |html2pdf.js / jsPDF                       |
|Build Tool        |Vite                                      |

-----

## 1. โครงสร้างโปรเจกต์ (Project Structure)

```
src/
├── App.vue
├── main.ts
├── assets/
│   └── styles/
│       └── variables.scss          # Vuetify custom theme
│
├── router/
│   └── index.ts                    # Vue Router + Navigation Guards
│
├── stores/                         # Pinia Stores
│   ├── auth.store.ts               # Authentication & User session
│   ├── application.store.ts        # GAP application CRUD
│   ├── inspection.store.ts         # Inspection & checklist
│   ├── certificate.store.ts        # Certificate management
│   └── notification.store.ts       # Notifications
│
├── composables/                    # Shared Composition Functions
│   ├── useAuth.ts
│   ├── usePermission.ts
│   └── useNotification.ts
│
├── plugins/
│   ├── vuetify.ts                  # Vuetify configuration
│   └── axios.ts                    # Axios instance + interceptors
│
├── layouts/
│   ├── DefaultLayout.vue           # Sidebar + AppBar + Footer
│   └── AuthLayout.vue              # Login / SSO callback page
│
├── views/
│   ├── auth/
│   │   ├── LoginPage.vue
│   │   └── SsoCallbackPage.vue
│   │
│   ├── dashboard/
│   │   └── DashboardPage.vue
│   │
│   ├── application/
│   │   ├── ApplicationListPage.vue
│   │   ├── ApplicationFormPage.vue        # Step Form (v-stepper)
│   │   ├── ApplicationDetailPage.vue
│   │   └── GroupApplicationPage.vue
│   │
│   ├── inspection/
│   │   ├── InspectionSchedulePage.vue
│   │   ├── InspectionChecklistPage.vue
│   │   └── InspectionResultPage.vue
│   │
│   ├── certificate/
│   │   ├── CertificateListPage.vue
│   │   └── CertificateDetailPage.vue
│   │
│   └── admin/
│       ├── UserManagementPage.vue
│       └── SystemSettingPage.vue
│
├── components/
│   ├── common/
│   │   ├── AppConfirmDialog.vue          # v-dialog confirm/cancel
│   │   ├── AppStatusChip.vue             # v-chip for statuses
│   │   ├── AppFileUpload.vue             # File/image uploader
│   │   └── AppNotificationBell.vue       # Notification dropdown
│   │
│   ├── application/
│   │   ├── StepApplicantInfo.vue         # Step 1: ข้อมูลผู้ขอ
│   │   ├── StepPlotInfo.vue              # Step 2: แปลงปลูก
│   │   ├── StepProductionInfo.vue        # Step 3: การผลิต
│   │   ├── StepDocumentUpload.vue        # Step 4: เอกสาร
│   │   └── StepReviewSubmit.vue          # Step 5: ตรวจสอบ & ยืนยัน
│   │
│   ├── inspection/
│   │   ├── GapChecklist.vue              # Checklist form
│   │   └── InspectionPhotoUpload.vue     # Photo upload grid
│   │
│   └── certificate/
│       └── CertificatePreview.vue        # PDF preview & download
│
└── utils/
    ├── constants.ts                # Enums, status codes
    ├── validators.ts               # Vuetify form rules
    └── pdf-generator.ts            # Certificate PDF builder
```

-----

## 2. Roles & Permissions

### 2.1 Role Definition

|Role           |รหัส          |คำอธิบาย                        |
|---------------|-------------|------------------------------|
|**Farmer**     |`FARMER`     |เกษตรกรผู้ยื่นคำขอ GAP             |
|**Group Admin**|`GROUP_ADMIN`|หัวหน้ากลุ่มเกษตรกร จัดการคำขอรายกลุ่ม|
|**staff**    |`staff`    |เจ้าหน้าที่ตรวจเอกสาร / อนุมัติ      |
|**Inspector**  |`INSPECTOR`  |ผู้ตรวจประเมินแปลง               |
|**Admin**      |`ADMIN`      |ผู้ดูแลระบบ                      |

### 2.2 Permission Matrix

|Feature          |Farmer|Group Admin|staff|Inspector|Admin|
|-----------------|:----:|:---------:|:-----:|:-------:|:---:|
|ยื่นคำขอรายเดี่ยว     |✅     |✅          |❌      |❌        |❌    |
|ยื่นคำขอรายกลุ่ม      |❌     |✅          |❌      |❌        |❌    |
|แก้ไข/ยกเลิกคำขอ    |✅*    |✅*         |❌      |❌        |✅    |
|ดู Dashboard ตนเอง|✅     |✅          |✅      |✅        |✅    |
|ตรวจเอกสาร       |❌     |❌          |✅      |❌        |✅    |
|นัดตรวจแปลง       |❌     |❌          |✅      |✅        |✅    |
|บันทึกผลตรวจ GAP   |❌     |❌          |❌      |✅        |✅    |
|อนุมัติ/ปฏิเสธคำขอ    |❌     |❌          |✅      |❌        |✅    |
|ออกใบรับรอง       |❌     |❌          |✅      |❌        |✅    |
|จัดการผู้ใช้         |❌     |❌          |❌      |❌        |✅    |


> ** แก้ไข/ยกเลิกได้เฉพาะคำขอของตนเองที่สถานะยังไม่ถึงขั้นอนุมัติ*

### 2.3 Route Guard & Permission Composable

```typescript
// composables/usePermission.ts
import { useAuthStore } from '@/stores/auth.store'

export function usePermission() {
  const auth = useAuthStore()

  const hasRole = (roles: string[]) => roles.includes(auth.user?.role)

  const can = (action: string) => {
    const permissions: Record<string, string[]> = {
      'application:create':     ['FARMER', 'GROUP_ADMIN'],
      'application:create-group': ['GROUP_ADMIN'],
      'application:edit-own':   ['FARMER', 'GROUP_ADMIN'],
      'document:review':        ['staff', 'ADMIN'],
      'inspection:schedule':    ['staff', 'INSPECTOR', 'ADMIN'],
      'inspection:record':      ['INSPECTOR', 'ADMIN'],
      'application:approve':    ['staff', 'ADMIN'],
      'certificate:issue':      ['staff', 'ADMIN'],
      'user:manage':            ['ADMIN'],
    }
    return (permissions[action] || []).includes(auth.user?.role)
  }

  return { hasRole, can }
}
```

-----

## 3. Authentication — SSO Flow

### 3.1 Flow Diagram
┌─────────────────────────────────────────────────┐
│                 Landing / Login Page             │
│   [เข้าสู่ระบบด้วย SSO]   [สมัครสมาชิก]           │
└────────────┬────────────────────┬───────────────┘
             │                    │
      Login  │                    │ Register
             ▼                    ▼
   ┌──────────────────┐  ┌─────────────────────┐
   │   SSO Login Flow │  │  SSO Register Flow  │
   │ (OAuth 2.0 Code) │  │ (ลงทะเบียนผู้ใช้ใหม่) │
   └────────┬─────────┘  └──────────┬──────────┘
            │                       │
            │  access_token         │  access_token
            ▼                       ▼
   ┌──────────────────────────────────────────┐
   │           /auth/callback                 │
   │  Exchange code → token → fetch profile  │
   └────────────────────┬─────────────────────┘
                        │
                        ▼
   ┌──────────────────────────────────────────┐
   │         Portal Page  (/portal)           │
   │  แสดงเมนูระบบตามสิทธิ์ (Role-based)        │
   └──────────────────────────────────────────┘

### 3.2 Auth Store (Pinia)

```typescript
// stores/auth.store.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from '@/plugins/axios'

interface User {
  id: string
  fullName: string
  role: 'FARMER' | 'GROUP_ADMIN' | 'staff' | 'INSPECTOR' | 'ADMIN'
  email: string
  avatar?: string
}

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const userRole = computed(() => user.value?.role)

  async function loginWithSso() {
    const ssoUrl = `${import.meta.env.VITE_SSO_URL}/authorize`
      + `?client_id=${import.meta.env.VITE_SSO_CLIENT_ID}`
      + `&redirect_uri=${encodeURIComponent(window.location.origin + '/auth/callback')}`
      + `&response_type=code`
      + `&scope=openid profile email`
    window.location.href = ssoUrl
  }

  async function handleCallback(code: string) {
    const { data } = await axios.post('/auth/token', { code })
    token.value = data.accessToken
    axios.defaults.headers.common['Authorization'] = `Bearer ${data.accessToken}`

    const profile = await axios.get('/auth/me')
    user.value = profile.data
  }

  function logout() {
    user.value = null
    token.value = null
    delete axios.defaults.headers.common['Authorization']
    window.location.href = `${import.meta.env.VITE_SSO_URL}/logout`
  }

  return { user, token, isAuthenticated, userRole, loginWithSso, handleCallback, logout }
}, { persist: true })
```

### 3.3 SSO Callback Page

```vue
<!-- views/auth/SsoCallbackPage.vue -->
<template>
  <v-container class="d-flex justify-center align-center" style="min-height: 100vh">
    <v-progress-circular indeterminate size="64" color="primary" />
    <p class="ml-4 text-h6">กำลังเข้าสู่ระบบ...</p>
  </v-container>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

onMounted(async () => {
  const code = route.query.code as string
  if (code) {
    await auth.handleCallback(code)
    router.replace({ name: 'Dashboard' })
  } else {
    router.replace({ name: 'Login' })
  }
})
</script>
```

-----

## 4. Router Configuration

```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const routes = [
  // ── Auth ──
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginPage.vue'),
    meta: { layout: 'auth', requiresAuth: false },
  },
  {
    path: '/auth/callback',
    name: 'SsoCallback',
    component: () => import('@/views/auth/SsoCallbackPage.vue'),
    meta: { layout: 'auth', requiresAuth: false },
  },

  // ── Dashboard ──
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/dashboard/DashboardPage.vue'),
    meta: { requiresAuth: true },
  },

  // ── Application (คำขอ GAP) ──
  {
    path: '/applications',
    name: 'ApplicationList',
    component: () => import('@/views/application/ApplicationListPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/applications/new',
    name: 'ApplicationCreate',
    component: () => import('@/views/application/ApplicationFormPage.vue'),
    meta: { requiresAuth: true, roles: ['FARMER', 'GROUP_ADMIN'] },
  },
  {
    path: '/applications/group/new',
    name: 'GroupApplicationCreate',
    component: () => import('@/views/application/GroupApplicationPage.vue'),
    meta: { requiresAuth: true, roles: ['GROUP_ADMIN'] },
  },
  {
    path: '/applications/:id',
    name: 'ApplicationDetail',
    component: () => import('@/views/application/ApplicationDetailPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/applications/:id/edit',
    name: 'ApplicationEdit',
    component: () => import('@/views/application/ApplicationFormPage.vue'),
    meta: { requiresAuth: true, roles: ['FARMER', 'GROUP_ADMIN'] },
  },

  // ── Inspection (ตรวจประเมิน) ──
  {
    path: '/inspections',
    name: 'InspectionSchedule',
    component: () => import('@/views/inspection/InspectionSchedulePage.vue'),
    meta: { requiresAuth: true, roles: ['staff', 'INSPECTOR', 'ADMIN'] },
  },
  {
    path: '/inspections/:id/checklist',
    name: 'InspectionChecklist',
    component: () => import('@/views/inspection/InspectionChecklistPage.vue'),
    meta: { requiresAuth: true, roles: ['INSPECTOR', 'ADMIN'] },
  },
  {
    path: '/inspections/:id/result',
    name: 'InspectionResult',
    component: () => import('@/views/inspection/InspectionResultPage.vue'),
    meta: { requiresAuth: true, roles: ['staff', 'INSPECTOR', 'ADMIN'] },
  },

  // ── Certificate (ใบรับรอง) ──
  {
    path: '/certificates',
    name: 'CertificateList',
    component: () => import('@/views/certificate/CertificateListPage.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/certificates/:id',
    name: 'CertificateDetail',
    component: () => import('@/views/certificate/CertificateDetailPage.vue'),
    meta: { requiresAuth: true },
  },

  // ── Admin ──
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: () => import('@/views/admin/UserManagementPage.vue'),
    meta: { requiresAuth: true, roles: ['ADMIN'] },
  },
  {
    path: '/admin/settings',
    name: 'SystemSettings',
    component: () => import('@/views/admin/SystemSettingPage.vue'),
    meta: { requiresAuth: true, roles: ['ADMIN'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// ── Navigation Guard ──
router.beforeEach((to, _from, next) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return next({ name: 'Login' })
  }

  if (to.meta.roles && !to.meta.roles.includes(auth.userRole)) {
    return next({ name: 'Dashboard' })
  }

  next()
})

export default router
```

-----

## 5. Portal Page — หน้าเมนูระบบกลางgi

### 5.1 ภาพรวม Portal

หลังจาก Login สำเร็จ ผู้ใช้จะถูก redirect มาที่หน้า Portal (/portal) ซึ่งทำหน้าที่เป็น Single Entry Point สำหรับทุกระบบภายใต้กรมวิชาการเกษตร โดยแสดงเฉพาะระบบที่ผู้ใช้มีสิทธิ์เข้าถึงตาม Role ที่ได้รับ

Portal Layout:
┌──────────────────────จัด───────────────────────────────────────────┐
│  🌿 ระบบรับรองมาตรฐานพืช (Header)              [User] [Logout]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ยินดีต้อนรับ, [ชื่อผู้ใช้]  |  บทบาท: [Role]                   │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │
│  │  GAP     │  │  DOA     │  │ จดทะเบียน│  │  Health  │        │
│  │ Cert.   │  │ Factory  │  │ ส่งออก   │  │ Cert. 1  │        │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                       │
│  │  Health  │  │   EL     │  │  Admin   │                       │
│  │ Cert. 2  │  │ System   │  │ Backend  │                       │
│  └──────────┘  └──────────┘  └──────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

### 5.2 System Registry — นิยามระบบทั้งหมด

// utils/portal-systems.ts
export interface PortalSystem {
  id: string
  title: string
  titleEn: string
  description: string
  icon: string
  color: string
  routeName: string         // ชื่อ route หรือ external URL
  external?: boolean        // true = เปิด tab ใหม่ (microservice อื่น)
  externalUrl?: string
  requiredRoles: string[]   // [] = ทุก role เข้าได้
  badge?: string            // ข้อความ badge เช่น "ใหม่", "Beta"
}

export const PORTAL_SYSTEMS: PortalSystem[] = [
  {
    id: 'gap',
    title: 'ระบบการรับรองมาตรฐาน GAP',
    titleEn: 'GAP Certification System',
    description: 'ยื่นคำขอรับรอง ตรวจประเมินแปลง และออกใบรับรองมาตรฐาน GAP พืช',
    icon: 'mdi-leaf-circle',
    color: 'success',
    routeName: 'Dashboard',
    requiredRoles: [], // ทุก role
  },
  {
    id: 'doa-factory',
    title: 'ระบบการขึ้นทะเบียนโรงงานผลิตสินค้าพืช DOA',
    titleEn: 'DOA Factory & Certification Body Registration',
    description: 'ขึ้นทะเบียนโรงงานผลิตสินค้าพืช DOA และหน่วยรับรองโรงงาน (Certification Body: CB)',
    icon: 'mdi-factory',
    color: 'primary',
    routeName: 'DoaFactoryDashboard',
    requiredRoles: ['FARMER', 'GROUP_ADMIN', 'staff', 'ADMIN'],
  },
  {
    id: 'export-register',
    title: 'ระบบจดทะเบียนผู้ส่งออก',
    titleEn: 'Exporter Registration System',
    description: 'จดทะเบียนผู้ส่งออกสินค้าเกษตร และต่ออายุใบทะเบียน',
    icon: 'mdi-truck-delivery',
    color: 'orange',
    routeName: 'ExporterDashboard',
    requiredRoles: ['FARMER', 'GROUP_ADMIN', 'staff', 'ADMIN'],
  },
  {
    id: 'health-cert-controlled',
    title: 'ระบบ Health Certificate',
    titleEn: 'Health Certificate — Controlled Plants',
    description: 'ออก Health Certificate ตามประกาศพืชควบคุมเฉพาะ',
    icon: 'mdi-file-certificate',
    color: 'teal',
    routeName: 'HealthCertControlledDashboard',
    requiredRoles: ['FARMER', 'GROUP_ADMIN', 'staff', 'ADMIN'],
    badge: 'พืชควบคุม',
  },
  {
    id: 'health-cert-processed',
    title: 'ระบบ Health Certificate สินค้าเกษตรแปรรูปด้านพืช',
    titleEn: 'Health Certificate — Processed Agricultural Products',
    description: 'ออก Health Certificate สำหรับสินค้าเกษตรแปรรูปด้านพืช',
    icon: 'mdi-file-certificate-outline',
    color: 'cyan',
    routeName: 'HealthCertProcessedDashboard',
    requiredRoles: ['FARMER', 'GROUP_ADMIN', 'staff', 'ADMIN'],
    badge: 'สินค้าแปรรูป',
  },
  {
    id: 'establishment-list',
    title: 'ระบบการควบคุมพิเศษ Establishment List (EL)',
    titleEn: 'Establishment List Management System',
    description: 'บริหารจัดการบัญชีรายชื่อโรงคัดบรรจุสินค้าเกษตรเพื่อการส่งออก',
    icon: 'mdi-format-list-checks',
    color: 'indigo',
    routeName: 'EstablishmentListDashboard',
    requiredRoles: ['staff', 'INSPECTOR', 'ADMIN'],
  },
  {
    id: 'admin-backend',
    title: 'ระบบบริหารจัดการผู้ดูแลระบบ (Backend)',
    titleEn: 'Admin & Open API Management',
    description: 'บริหารจัดการผู้ใช้งาน สิทธิ์ระบบ และจัดการ Open API',
    icon: 'mdi-shield-crown',
    color: 'deep-purple',
    routeName: 'AdminPortal',
    requiredRoles: ['ADMIN'],
    badge: 'Admin',
  },
]

### 5.3 Portal Permission Composable

// composables/usePortalPermission.ts
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth.store'
import { PORTAL_SYSTEMS, type PortalSystem } from '@/utils/portal-systems'

export function usePortalPermission() {
  const auth = useAuthStore()

  const accessibleSystems = computed<PortalSystem[]>(() =>
    PORTAL_SYSTEMS.filter(sys => {
      if (sys.requiredRoles.length === 0) return true
      return sys.requiredRoles.includes(auth.user?.role ?? '')
    })
  )

  const hasAccessTo = (systemId: string) =>
    accessibleSystems.value.some(s => s.id === systemId)

  return { accessibleSystems, hasAccessTo }
}

### 5.4 Portal Page Component

<!-- views/portal/PortalPage.vue -->
<template>
  <v-app :theme="'gapTheme'">

    <!-- App Bar -->
    <v-app-bar flat color="primary" elevation="2">
      <v-app-bar-title>
        <div class="d-flex align-center">
          <v-icon size="28" color="white" class="mr-2">mdi-leaf</v-icon>
          <span class="text-white font-weight-bold">ระบบรับรองมาตรฐานพืช</span>
          <span class="text-white text-caption ml-2 opacity-70">กรมวิชาการเกษตร</span>
        </div>
      </v-app-bar-title>
      <template v-slot:append>
        <AppNotificationBell />
        <v-menu>
          <template v-slot:activator="{ props }">
            <v-btn v-bind="props" variant="text" class="text-white ml-1">
              <v-avatar color="white" size="32" class="mr-2">
                <span class="text-primary font-weight-bold text-body-2">
                  {{ auth.user?.fullName?.charAt(0) }}
                </span>
              </v-avatar>
              {{ auth.user?.fullName }}
              <v-icon end>mdi-chevron-down</v-icon>
            </v-btn>
          </template>
          <v-list min-width="220">
            <v-list-item
              prepend-icon="mdi-account-circle"
              :title="auth.user?.fullName"
              :subtitle="roleLabel"
            />
            <v-divider />
            <v-list-item
              prepend-icon="mdi-account-edit"
              title="แก้ไขโปรไฟล์"
              @click="router.push({ name: 'UserProfile' })"
            />
            <v-list-item
              prepend-icon="mdi-logout"
              title="ออกจากระบบ"
              @click="auth.logout()"
              base-color="error"
            />
          </v-list>
        </v-menu>
      </template>
    </v-app-bar>

    <v-main class="portal-bg">
      <v-container class="py-8" max-width="1200">

        <!-- Welcome Banner -->
        <v-card color="primary" variant="tonal" class="mb-8" rounded="xl">
          <v-card-text class="d-flex align-center pa-6">
            <div>
              <h2 class="text-h5 font-weight-bold">
                ยินดีต้อนรับ, {{ auth.user?.fullName }} 👋
              </h2>
              <p class="text-body-2 mt-1 text-medium-emphasis">
                บทบาท: <v-chip size="small" color="primary" class="ml-1">{{ roleLabel }}</v-chip>
                &nbsp;|&nbsp; สิทธิ์เข้าถึง {{ accessibleSystems.length }} ระบบ
              </p>
            </div>
            <v-spacer />
            <v-icon size="80" color="primary" class="opacity-20">mdi-leaf-circle</v-icon>
          </v-card-text>
        </v-card>

        <!-- Systems Grid -->
        <h2 class="text-h6 font-weight-bold mb-4">
          <v-icon start color="primary">mdi-apps</v-icon>
          ระบบที่คุณสามารถเข้าใช้งาน
        </h2>

        <v-row>
          <v-col
            v-for="system in accessibleSystems"
            :key="system.id"
            cols="12" sm="6" md="4" lg="3"
          >
            <v-card
              rounded="xl"
              elevation="2"
              class="system-card h-100"
              hover
              @click="navigateTo(system)"
            >
              <v-card-text class="pa-6">
                <!-- Badge -->
                <div class="d-flex justify-space-between align-start mb-4">
                  <v-avatar :color="system.color" size="56" rounded="lg">
                    <v-icon size="30" color="white">{{ system.icon }}</v-icon>
                  </v-avatar>
                  <v-chip
                    v-if="system.badge"
                    :color="system.color"
                    size="x-small"
                    label
                  >
                    {{ system.badge }}
                  </v-chip>
                </div>

                <!-- Title -->
                <h3 class="text-subtitle-1 font-weight-bold mb-2 system-title">
                  {{ system.title }}
                </h3>
                <p class="text-caption text-medium-emphasis">
                  {{ system.description }}
                </p>
              </v-card-text>

              <v-card-actions class="pa-4 pt-0">
                <v-btn
                  :color="system.color"
                  variant="tonal"
                  size="small"
                  rounded="lg"
                  block
                >
                  <v-icon start size="16">mdi-arrow-right-circle</v-icon>
                  เข้าใช้งาน
                </v-btn>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>

        <!-- No access message -->
        <v-card
          v-if="accessibleSystems.length === 0"
          variant="outlined"
          rounded="xl"
          class="mt-4"
        >
          <v-card-text class="text-center pa-12">
            <v-icon size="64" color="grey-lighten-1">mdi-lock-outline</v-icon>
            <p class="text-h6 mt-4 text-medium-emphasis">ยังไม่มีสิทธิ์เข้าใช้งานระบบ</p>
            <p class="text-body-2 text-medium-emphasis">กรุณาติดต่อผู้ดูแลระบบเพื่อขอสิทธิ์</p>
          </v-card-text>
        </v-card>

      </v-container>
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { usePortalPermission } from '@/composables/usePortalPermission'
import { type PortalSystem } from '@/utils/portal-systems'
import AppNotificationBell from '@/components/common/AppNotificationBell.vue'

const auth = useAuthStore()
const router = useRouter()
const { accessibleSystems } = usePortalPermission()

const roleLabels: Record<string, string> = {
  FARMER:      'เกษตรกร',
  GROUP_ADMIN: 'หัวหน้ากลุ่มเกษตรกร',
  staff:     'เจ้าหน้าที่',
  INSPECTOR:   'ผู้ตรวจประเมิน',
  ADMIN:       'ผู้ดูแลระบบ',
}

const roleLabel = computed(() => roleLabels[auth.user?.role ?? ''] ?? auth.user?.role)

function navigateTo(system: PortalSystem) {
  if (system.external && system.externalUrl) {
    window.open(system.externalUrl, '_blank')
  } else {
    router.push({ name: system.routeName })
  }
}
</script>

<style scoped>
.portal-bg {
  background: linear-gradient(160deg, #F1F8E9 0%, #E8F5E9 40%, #E0F7FA 100%);
  min-height: 100vh;
}

.system-card {
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.system-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
}

.system-title {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.4;
  min-height: 2.8em;
}
</style>

```

-----


## 6. Application Step Form (v-stepper)

### 6.1 หน้า Step Form หลัก

```vue
<!-- views/application/ApplicationFormPage.vue -->
<template>
  <v-container>
    <v-card>
      <v-card-title class="text-h5 pa-6">
        <v-icon start>mdi-file-document-edit</v-icon>
        ยื่นคำขอรับรอง GAP พืช
      </v-card-title>

      <v-stepper v-model="currentStep" :items="stepItems" alt-labels>
        <!-- Step 1: ข้อมูลผู้ขอ -->
        <template v-slot:item.1>
          <StepApplicantInfo
            v-model="form.applicant"
            ref="step1Ref"
          />
        </template>

        <!-- Step 2: แปลงปลูก -->
        <template v-slot:item.2>
          <StepPlotInfo
            v-model="form.plots"
            ref="step2Ref"
          />
        </template>

        <!-- Step 3: การผลิต -->
        <template v-slot:item.3>
          <StepProductionInfo
            v-model="form.production"
            ref="step3Ref"
          />
        </template>

        <!-- Step 4: เอกสาร -->
        <template v-slot:item.4>
          <StepDocumentUpload
            v-model="form.documents"
            ref="step4Ref"
          />
        </template>

        <!-- Step 5: ตรวจสอบ & ยืนยัน -->
        <template v-slot:item.5>
          <StepReviewSubmit :form-data="form" />
        </template>

        <!-- Actions -->
        <template v-slot:actions>
          <v-btn
            v-if="currentStep > 1"
            variant="text"
            @click="currentStep--"
          >
            <v-icon start>mdi-arrow-left</v-icon>
            ย้อนกลับ
          </v-btn>

          <v-spacer />

          <v-btn color="grey" variant="outlined" class="mr-2" @click="saveDraft">
            <v-icon start>mdi-content-save</v-icon>
            บันทึกร่าง
          </v-btn>

          <v-btn
            v-if="currentStep < 5"
            color="primary"
            @click="goNext"
          >
            ถัดไป
            <v-icon end>mdi-arrow-right</v-icon>
          </v-btn>

          <v-btn
            v-else
            color="success"
            @click="submitApplication"
            :loading="isSubmitting"
          >
            <v-icon start>mdi-send</v-icon>
            ยื่นคำขอ
          </v-btn>
        </template>
      </v-stepper>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useApplicationStore } from '@/stores/application.store'
import StepApplicantInfo from '@/components/application/StepApplicantInfo.vue'
import StepPlotInfo from '@/components/application/StepPlotInfo.vue'
import StepProductionInfo from '@/components/application/StepProductionInfo.vue'
import StepDocumentUpload from '@/components/application/StepDocumentUpload.vue'
import StepReviewSubmit from '@/components/application/StepReviewSubmit.vue'

const router = useRouter()
const appStore = useApplicationStore()

const currentStep = ref(1)
const isSubmitting = ref(false)
const step1Ref = ref()
const step2Ref = ref()
const step3Ref = ref()
const step4Ref = ref()

const stepItems = [
  { title: 'ข้อมูลผู้ขอ', value: 1 },
  { title: 'แปลงปลูก',   value: 2 },
  { title: 'การผลิต',     value: 3 },
  { title: 'เอกสาร',      value: 4 },
  { title: 'ตรวจสอบ',     value: 5 },
]

const form = reactive({
  applicant: { fullName: '', idCard: '', phone: '', address: '' },
  plots: [],
  production: { cropType: '', area: '', method: '', startDate: '' },
  documents: [],
})

async function goNext() {
  const refs = [step1Ref, step2Ref, step3Ref, step4Ref]
  const stepRef = refs[currentStep.value - 1]
  const { valid } = await stepRef.value.validate()
  if (valid) currentStep.value++
}

async function saveDraft() {
  await appStore.saveDraft(form)
}

async function submitApplication() {
  isSubmitting.value = true
  try {
    await appStore.submit(form)
    router.push({ name: 'ApplicationList' })
  } finally {
    isSubmitting.value = false
  }
}
</script>
```

### 6.2 Step 1 — ข้อมูลผู้ขอ (ตัวอย่าง Component)

```vue
<!-- components/application/StepApplicantInfo.vue -->
<template>
  <v-form ref="formRef">
    <v-card flat>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="model.fullName"
              label="ชื่อ-นามสกุล"
              :rules="[rules.required]"
              prepend-inner-icon="mdi-account"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="model.idCard"
              label="เลขบัตรประชาชน"
              :rules="[rules.required, rules.idCard]"
              prepend-inner-icon="mdi-card-account-details"
              maxlength="13"
            />
          </v-col>
          <v-col cols="12" md="6">
            <v-text-field
              v-model="model.phone"
              label="เบอร์โทรศัพท์"
              :rules="[rules.required, rules.phone]"
              prepend-inner-icon="mdi-phone"
            />
          </v-col>
          <v-col cols="12">
            <v-textarea
              v-model="model.address"
              label="ที่อยู่"
              :rules="[rules.required]"
              rows="3"
              prepend-inner-icon="mdi-map-marker"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const model = defineModel({ required: true })
const formRef = ref()

const rules = {
  required: (v: string) => !!v || 'กรุณากรอกข้อมูล',
  idCard: (v: string) => /^\d{13}$/.test(v) || 'เลขบัตรประชาชนไม่ถูกต้อง',
  phone: (v: string) => /^0\d{8,9}$/.test(v) || 'เบอร์โทรไม่ถูกต้อง',
}

function validate() {
  return formRef.value.validate()
}

defineExpose({ validate })
</script>
```

### 6.3 Step 2 — แปลงปลูก (Dynamic Plot List)

```vue
<!-- components/application/StepPlotInfo.vue -->
<template>
  <v-form ref="formRef">
    <v-card flat>
      <v-card-text>
        <div v-for="(plot, index) in model" :key="index" class="mb-4">
          <v-card variant="outlined">
            <v-card-title class="d-flex align-center">
              แปลงที่ {{ index + 1 }}
              <v-spacer />
              <v-btn
                icon="mdi-delete"
                color="error"
                size="small"
                variant="text"
                @click="removePlot(index)"
                v-if="model.length > 1"
              />
            </v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model="plot.plotName"
                    label="ชื่อแปลง"
                    :rules="[rules.required]"
                  />
                </v-col>
                <v-col cols="12" md="4">
                  <v-text-field
                    v-model.number="plot.area"
                    label="พื้นที่ (ไร่)"
                    type="number"
                    :rules="[rules.required, rules.positive]"
                  />
                </v-col>
                <v-col cols="12" md="4">
                  <v-select
                    v-model="plot.province"
                    label="จังหวัด"
                    :items="provinces"
                    :rules="[rules.required]"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="plot.latitude"
                    label="ละติจูด"
                    type="number"
                    step="0.000001"
                  />
                </v-col>
                <v-col cols="12" md="6">
                  <v-text-field
                    v-model.number="plot.longitude"
                    label="ลองจิจูด"
                    type="number"
                    step="0.000001"
                  />
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>
        </div>

        <v-btn color="primary" variant="outlined" block @click="addPlot">
          <v-icon start>mdi-plus</v-icon>
          เพิ่มแปลง
        </v-btn>
      </v-card-text>
    </v-card>
  </v-form>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const model = defineModel<any[]>({ required: true, default: () => [createEmptyPlot()] })
const formRef = ref()
const provinces = ['กรุงเทพมหานคร', 'เชียงใหม่', 'ขอนแก่น', 'นครราชสีมา', '...']

const rules = {
  required: (v: any) => !!v || 'กรุณากรอกข้อมูล',
  positive: (v: number) => v > 0 || 'กรุณากรอกค่ามากกว่า 0',
}

function createEmptyPlot() {
  return { plotName: '', area: null, province: '', latitude: null, longitude: null }
}

function addPlot() { model.value.push(createEmptyPlot()) }
function removePlot(i: number) { model.value.splice(i, 1) }
function validate() { return formRef.value.validate() }

defineExpose({ validate })
</script>
```

-----

## 7. Dashboard

### 7.1 Dashboard Layout

```vue
<!-- views/dashboard/DashboardPage.vue -->
<template>
  <v-container>
    <h1 class="text-h4 mb-6">Dashboard</h1>

    <!-- ── Summary Cards ── -->
    <v-row>
      <v-col v-for="card in summaryCards" :key="card.title" cols="12" sm="6" md="3">
        <v-card :color="card.color" variant="tonal">
          <v-card-text class="d-flex align-center">
            <v-icon :icon="card.icon" size="48" class="mr-4" />
            <div>
              <div class="text-h4 font-weight-bold">{{ card.value }}</div>
              <div class="text-body-2">{{ card.title }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- ── Notifications ── -->
    <v-card class="mt-6">
      <v-card-title>
        <v-icon start>mdi-bell</v-icon>
        การแจ้งเตือนล่าสุด
      </v-card-title>
      <v-list>
        <v-list-item
          v-for="noti in notifications"
          :key="noti.id"
          :prepend-icon="noti.icon"
          :subtitle="noti.date"
        >
          <v-list-item-title>{{ noti.message }}</v-list-item-title>
          <template v-slot:append>
            <AppStatusChip :status="noti.status" />
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- ── Recent Applications Table ── -->
    <v-card class="mt-6">
      <v-card-title>
        <v-icon start>mdi-file-document</v-icon>
        คำขอล่าสุด
      </v-card-title>
      <v-data-table
        :headers="tableHeaders"
        :items="recentApplications"
        :items-per-page="5"
        density="comfortable"
      >
        <template v-slot:item.status="{ value }">
          <AppStatusChip :status="value" />
        </template>
        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            :to="{ name: 'ApplicationDetail', params: { id: item.id } }"
          />
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth.store'
import { useApplicationStore } from '@/stores/application.store'
import { useNotificationStore } from '@/stores/notification.store'
import AppStatusChip from '@/components/common/AppStatusChip.vue'

const auth = useAuthStore()
const appStore = useApplicationStore()
const notiStore = useNotificationStore()

onMounted(async () => {
  await appStore.fetchDashboardSummary()
  await notiStore.fetchRecent()
})

const summaryCards = computed(() => [
  { title: 'คำขอทั้งหมด',       value: appStore.summary.total,     icon: 'mdi-file-multiple',        color: 'primary' },
  { title: 'รอดำเนินการ',       value: appStore.summary.pending,   icon: 'mdi-clock-outline',        color: 'warning' },
  { title: 'ผ่านการรับรอง',      value: appStore.summary.approved,  icon: 'mdi-check-circle-outline', color: 'success' },
  { title: 'ใบรับรองที่ใช้งานอยู่', value: appStore.summary.activeCerts, icon: 'mdi-certificate',       color: 'info'    },
])

const notifications = computed(() => notiStore.items)
const recentApplications = computed(() => appStore.recentList)

const tableHeaders = [
  { title: 'เลขที่คำขอ',   key: 'applicationNo' },
  { title: 'ประเภทพืช',    key: 'cropType' },
  { title: 'วันที่ยื่น',      key: 'submittedAt' },
  { title: 'สถานะ',        key: 'status' },
  { title: '',             key: 'actions', sortable: false },
]
</script>
```

### 7.2 Status Chip Component

```vue
<!-- components/common/AppStatusChip.vue -->
<template>
  <v-chip :color="statusColor" size="small" label>
    <v-icon start size="14">{{ statusIcon }}</v-icon>
    {{ statusLabel }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ status: string }>()

const statusMap: Record<string, { color: string; icon: string; label: string }> = {
  DRAFT:             { color: 'grey',    icon: 'mdi-pencil',           label: 'ร่าง' },
  SUBMITTED:         { color: 'blue',    icon: 'mdi-send',             label: 'ยื่นแล้ว' },
  DOC_REVIEW:        { color: 'orange',  icon: 'mdi-file-search',      label: 'ตรวจเอกสาร' },
  INSPECTION_SCHEDULED: { color: 'purple', icon: 'mdi-calendar-clock', label: 'นัดตรวจ' },
  INSPECTING:        { color: 'indigo',  icon: 'mdi-clipboard-check',  label: 'กำลังตรวจ' },
  APPROVED:          { color: 'green',   icon: 'mdi-check-circle',     label: 'อนุมัติ' },
  REJECTED:          { color: 'red',     icon: 'mdi-close-circle',     label: 'ไม่ผ่าน' },
  CANCELLED:         { color: 'grey',    icon: 'mdi-cancel',           label: 'ยกเลิก' },
  CERT_ISSUED:       { color: 'teal',    icon: 'mdi-certificate',      label: 'ออกใบรับรอง' },
  CERT_EXPIRED:      { color: 'brown',   icon: 'mdi-clock-alert',      label: 'หมดอายุ' },
}

const current = computed(() => statusMap[props.status] || statusMap.DRAFT)
const statusColor = computed(() => current.value.color)
const statusIcon = computed(() => current.value.icon)
const statusLabel = computed(() => current.value.label)
</script>
```

-----

## 8. Application State Flow

```
                    ┌────────┐
         ┌─────────│ DRAFT  │──────── บันทึกร่าง
         │         └───┬────┘
         │ ยกเลิก       │ ยื่นคำขอ
         ▼             ▼
   ┌───────────┐  ┌───────────┐
   │ CANCELLED │  │ SUBMITTED │
   └───────────┘  └─────┬─────┘
                        │ เจ้าหน้าที่รับเรื่อง
                        ▼
                  ┌────────────┐
                  │ DOC_REVIEW │ ─── ตรวจเอกสาร
                  └─────┬──────┘
            เอกสารไม่ผ่าน │          │ เอกสารผ่าน
            (ส่งกลับแก้ไข)│          ▼
                  ▲      │    ┌─────────────────────┐
                  │      │    │ INSPECTION_SCHEDULED │ ─── นัดตรวจแปลง
                  │      │    └──────────┬──────────┘
                  │      │               ▼
                  │      │         ┌────────────┐
                  │      │         │ INSPECTING │ ─── บันทึกผลตรวจ
                  │      │         └─────┬──────┘
                  │      │     ไม่ผ่าน    │      ผ่าน
                  │      │        ┌──────┴──────┐
                  │      ▼        ▼             ▼
                  │  ┌──────────┐          ┌──────────┐
                  │  │ REJECTED │          │ APPROVED │
                  │  └──────────┘          └────┬─────┘
                  │                             │ ออกใบรับรอง
                  │                             ▼
                  │                       ┌─────────────┐
                  │                       │ CERT_ISSUED │
                  │                       └──────┬──────┘
                  │                              │ หมดอายุ
                  │                              ▼
                  │                       ┌──────────────┐
                  └───────────────────────│ CERT_EXPIRED │ ── ยื่นต่ออายุ (loop)
                                          └──────────────┘
```

-----

## 9. Inspection Module

### 9.1 GAP Checklist Component

```vue
<!-- components/inspection/GapChecklist.vue -->
<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-clipboard-check-outline</v-icon>
      รายการตรวจประเมิน GAP
    </v-card-title>

    <v-card-text>
      <v-expansion-panels variant="accordion">
        <v-expansion-panel
          v-for="(category, ci) in checklist"
          :key="ci"
          :title="category.title"
        >
          <v-expansion-panel-text>
            <v-table density="compact">
              <thead>
                <tr>
                  <th style="width: 50%">ข้อกำหนด</th>
                  <th style="width: 20%">ผลตรวจ</th>
                  <th style="width: 30%">หมายเหตุ</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, ii) in category.items" :key="ii">
                  <td>{{ item.label }}</td>
                  <td>
                    <v-btn-toggle
                      v-model="item.result"
                      mandatory
                      density="compact"
                      color="primary"
                    >
                      <v-btn value="PASS" size="small" color="success">ผ่าน</v-btn>
                      <v-btn value="FAIL" size="small" color="error">ไม่ผ่าน</v-btn>
                      <v-btn value="NA"   size="small">N/A</v-btn>
                    </v-btn-toggle>
                  </td>
                  <td>
                    <v-text-field
                      v-model="item.remark"
                      density="compact"
                      variant="underlined"
                      hide-details
                      placeholder="หมายเหตุ"
                    />
                  </td>
                </tr>
              </tbody>
            </v-table>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
interface CheckItem {
  label: string
  result: 'PASS' | 'FAIL' | 'NA' | null
  remark: string
}

interface CheckCategory {
  title: string
  items: CheckItem[]
}

const checklist = defineModel<CheckCategory[]>({ required: true })
</script>
```

### 9.2 GAP Checklist Data (ตัวอย่าง)

```typescript
// utils/gap-checklist-template.ts
export const GAP_CHECKLIST_TEMPLATE = [
  {
    title: '1. แหล่งน้ำ',
    items: [
      { label: '1.1 แหล่งน้ำไม่มีการปนเปื้อนสารเคมี',       result: null, remark: '' },
      { label: '1.2 มีระบบการจัดการน้ำอย่างเหมาะสม',         result: null, remark: '' },
      { label: '1.3 มีการตรวจวิเคราะห์คุณภาพน้ำ',            result: null, remark: '' },
    ],
  },
  {
    title: '2. พื้นที่ปลูก',
    items: [
      { label: '2.1 พื้นที่ไม่มีสารปนเปื้อนในดิน',              result: null, remark: '' },
      { label: '2.2 ไม่อยู่ใกล้แหล่งมลพิษ',                   result: null, remark: '' },
      { label: '2.3 มีการจัดการดินอย่างเหมาะสม',              result: null, remark: '' },
    ],
  },
  {
    title: '3. วัตถุอันตรายทางการเกษตร',
    items: [
      { label: '3.1 ใช้สารเคมีตามคำแนะนำ',                   result: null, remark: '' },
      { label: '3.2 มีการเก็บรักษาสารเคมีอย่างปลอดภัย',        result: null, remark: '' },
      { label: '3.3 ผู้ใช้สารเคมีมีอุปกรณ์ป้องกัน',              result: null, remark: '' },
    ],
  },
  {
    title: '4. การจัดการคุณภาพในกระบวนการผลิตก่อนการเก็บเกี่ยว',
    items: [
      { label: '4.1 ใช้พันธุ์พืชที่เหมาะสม',                     result: null, remark: '' },
      { label: '4.2 มีการจดบันทึกการผลิต',                     result: null, remark: '' },
    ],
  },
  {
    title: '5. การเก็บเกี่ยวและการปฏิบัติหลังเก็บเกี่ยว',
    items: [
      { label: '5.1 เก็บเกี่ยวในระยะเวลาเหมาะสม',              result: null, remark: '' },
      { label: '5.2 ภาชนะสะอาดและเหมาะสม',                  result: null, remark: '' },
      { label: '5.3 สถานที่เก็บรักษาสะอาดปลอดภัย',             result: null, remark: '' },
    ],
  },
  {
    title: '6. การพักผ่อนของสารเคมี',
    items: [
      { label: '6.1 ปฏิบัติตามระยะเวลาหยุดใช้สารเคมีก่อนเก็บเกี่ยว', result: null, remark: '' },
    ],
  },
  {
    title: '7. การบันทึกข้อมูลและการตามสอบ',
    items: [
      { label: '7.1 มีบันทึกการใช้ปัจจัยการผลิต',                result: null, remark: '' },
      { label: '7.2 สามารถตามสอบได้ตลอดห่วงโซ่',              result: null, remark: '' },
    ],
  },
  {
    title: '8. สุขลักษณะส่วนบุคคล',
    items: [
      { label: '8.1 ผู้ปฏิบัติงานมีสุขลักษณะที่ดี',               result: null, remark: '' },
      { label: '8.2 มีสิ่งอำนวยความสะดวกด้านสุขอนามัย',        result: null, remark: '' },
    ],
  },
]
```

### 9.3 Photo Upload for Inspection

```vue
<!-- components/inspection/InspectionPhotoUpload.vue -->
<template>
  <v-card>
    <v-card-title>
      <v-icon start>mdi-camera</v-icon>
      อัปโหลดรูปภาพการตรวจ
    </v-card-title>

    <v-card-text>
      <v-file-input
        v-model="newFiles"
        label="เลือกรูปภาพ"
        accept="image/*"
        multiple
        prepend-icon="mdi-camera-plus"
        show-size
        chips
        @update:model-value="onFilesSelected"
      />

      <v-row class="mt-2">
        <v-col
          v-for="(photo, index) in photos"
          :key="index"
          cols="6" sm="4" md="3"
        >
          <v-card variant="outlined">
            <v-img :src="photo.preview" height="150" cover />
            <v-card-text class="pa-2">
              <v-text-field
                v-model="photo.caption"
                density="compact"
                variant="underlined"
                placeholder="คำอธิบายรูป"
                hide-details
              />
            </v-card-text>
            <v-card-actions class="pa-1">
              <v-spacer />
              <v-btn icon="mdi-delete" color="error" size="small" @click="removePhoto(index)" />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import { ref } from 'vue'

interface Photo { file: File; preview: string; caption: string }

const photos = defineModel<Photo[]>({ default: () => [] })
const newFiles = ref<File[]>([])

function onFilesSelected(files: File[]) {
  if (!files) return
  for (const file of files) {
    const preview = URL.createObjectURL(file)
    photos.value.push({ file, preview, caption: '' })
  }
  newFiles.value = []
}

function removePhoto(index: number) {
  URL.revokeObjectURL(photos.value[index].preview)
  photos.value.splice(index, 1)
}
</script>
```

-----

## 10. Certificate Module

### 10.1 Certificate List (v-data-table)

```vue
<!-- views/certificate/CertificateListPage.vue -->
<template>
  <v-container>
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-certificate</v-icon>
        ใบรับรอง GAP
        <v-spacer />
        <v-text-field
          v-model="search"
          prepend-inner-icon="mdi-magnify"
          label="ค้นหา"
          density="compact"
          variant="outlined"
          hide-details
          class="ml-4"
          style="max-width: 300px"
        />
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="certificates"
        :search="search"
        :loading="loading"
        hover
      >
        <template v-slot:item.status="{ value }">
          <AppStatusChip :status="value" />
        </template>

        <template v-slot:item.expiryDate="{ value }">
          <span :class="isExpiringSoon(value) ? 'text-warning font-weight-bold' : ''">
            {{ formatDate(value) }}
          </span>
        </template>

        <template v-slot:item.actions="{ item }">
          <v-btn
            icon="mdi-eye"
            size="small"
            variant="text"
            :to="{ name: 'CertificateDetail', params: { id: item.id } }"
          />
          <v-btn
            icon="mdi-download"
            size="small"
            variant="text"
            color="primary"
            @click="downloadPdf(item.id)"
          />
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useCertificateStore } from '@/stores/certificate.store'
import AppStatusChip from '@/components/common/AppStatusChip.vue'

const certStore = useCertificateStore()
const search = ref('')
const loading = ref(false)

const headers = [
  { title: 'เลขที่ใบรับรอง', key: 'certNo' },
  { title: 'เกษตรกร',       key: 'farmerName' },
  { title: 'ชนิดพืช',        key: 'cropType' },
  { title: 'วันที่ออก',       key: 'issuedDate' },
  { title: 'วันหมดอายุ',     key: 'expiryDate' },
  { title: 'สถานะ',         key: 'status' },
  { title: '',              key: 'actions', sortable: false },
]

const certificates = ref([])

onMounted(async () => {
  loading.value = true
  certificates.value = await certStore.fetchAll()
  loading.value = false
})

function formatDate(d: string) {
  return new Date(d).toLocaleDateString('th-TH', { year: 'numeric', month: 'short', day: 'numeric' })
}

function isExpiringSoon(d: string) {
  const diff = new Date(d).getTime() - Date.now()
  return diff > 0 && diff < 30 * 24 * 60 * 60 * 1000
}

async function downloadPdf(id: string) {
  await certStore.downloadPdf(id)
}
</script>
```

### 10.2 Certificate PDF Generation

```typescript
// utils/pdf-generator.ts
import jsPDF from 'jspdf'

interface CertData {
  certNo: string
  farmerName: string
  idCard: string
  cropType: string
  plotAddress: string
  area: string
  issuedDate: string
  expiryDate: string
  inspectorName: string
  approverName: string
}

export function generateCertificatePdf(data: CertData): jsPDF {
  const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })

  // Border
  doc.setDrawColor(34, 139, 34)
  doc.setLineWidth(2)
  doc.rect(10, 10, 277, 190)
  doc.setLineWidth(0.5)
  doc.rect(14, 14, 269, 182)

  // Header
  doc.setFontSize(24)
  doc.setTextColor(34, 139, 34)
  doc.text('ใบรับรองแหล่งผลิต GAP พืช', 148.5, 40, { align: 'center' })

  doc.setFontSize(14)
  doc.text('Certificate of Good Agricultural Practices', 148.5, 50, { align: 'center' })

  // Certificate Number
  doc.setFontSize(12)
  doc.setTextColor(0, 0, 0)
  doc.text(`เลขที่ใบรับรอง: ${data.certNo}`, 148.5, 65, { align: 'center' })

  // Content
  doc.setFontSize(11)
  const startY = 80
  const lineHeight = 10
  const lines = [
    `ขอรับรองว่า ${data.farmerName}`,
    `เลขบัตรประชาชน: ${data.idCard}`,
    `ได้ผ่านการตรวจประเมินแปลงผลิตพืช: ${data.cropType}`,
    `สถานที่ตั้ง: ${data.plotAddress}`,
    `พื้นที่: ${data.area} ไร่`,
    `ตามมาตรฐาน GAP (Good Agricultural Practices)`,
  ]

  lines.forEach((line, i) => {
    doc.text(line, 40, startY + i * lineHeight)
  })

  // Dates
  doc.text(`วันที่ออกใบรับรอง: ${data.issuedDate}`, 40, 155)
  doc.text(`วันหมดอายุ: ${data.expiryDate}`, 40, 165)

  // Signatures
  doc.text('ผู้ตรวจประเมิน', 80, 185, { align: 'center' })
  doc.text(data.inspectorName, 80, 192, { align: 'center' })
  doc.line(40, 182, 120, 182)

  doc.text('ผู้อนุมัติ', 220, 185, { align: 'center' })
  doc.text(data.approverName, 220, 192, { align: 'center' })
  doc.line(180, 182, 260, 182)

  return doc
}
```

### 10.3 Certificate Store

```typescript
// stores/certificate.store.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from '@/plugins/axios'
import { generateCertificatePdf } from '@/utils/pdf-generator'

export const useCertificateStore = defineStore('certificate', () => {
  const certificates = ref([])
  const current = ref(null)

  async function fetchAll() {
    const { data } = await axios.get('/certificates')
    certificates.value = data
    return data
  }

  async function fetchById(id: string) {
    const { data } = await axios.get(`/certificates/${id}`)
    current.value = data
    return data
  }

  async function downloadPdf(id: string) {
    const cert = await fetchById(id)
    const pdf = generateCertificatePdf(cert)
    pdf.save(`GAP-Certificate-${cert.certNo}.pdf`)
  }

  return { certificates, current, fetchAll, fetchById, downloadPdf }
})
```

-----

## 11. Application Store (Pinia)

```typescript
// stores/application.store.ts
import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import axios from '@/plugins/axios'

interface DashboardSummary {
  total: number
  pending: number
  approved: number
  activeCerts: number
}

export const useApplicationStore = defineStore('application', () => {
  const summary = reactive<DashboardSummary>({ total: 0, pending: 0, approved: 0, activeCerts: 0 })
  const recentList = ref([])
  const currentApp = ref(null)

  async function fetchDashboardSummary() {
    const { data } = await axios.get('/applications/summary')
    Object.assign(summary, data)
    const recent = await axios.get('/applications?limit=10&sort=-submittedAt')
    recentList.value = recent.data
  }

  async function fetchById(id: string) {
    const { data } = await axios.get(`/applications/${id}`)
    currentApp.value = data
    return data
  }

  async function saveDraft(form: any) {
    if (form.id) {
      await axios.put(`/applications/${form.id}`, { ...form, status: 'DRAFT' })
    } else {
      const { data } = await axios.post('/applications', { ...form, status: 'DRAFT' })
      form.id = data.id
    }
  }

  async function submit(form: any) {
    if (form.id) {
      await axios.put(`/applications/${form.id}`, { ...form, status: 'SUBMITTED' })
    } else {
      await axios.post('/applications', { ...form, status: 'SUBMITTED' })
    }
  }

  async function cancel(id: string) {
    await axios.patch(`/applications/${id}/status`, { status: 'CANCELLED' })
  }

  async function updateStatus(id: string, status: string, payload?: any) {
    await axios.patch(`/applications/${id}/status`, { status, ...payload })
  }

  return { summary, recentList, currentApp, fetchDashboardSummary, fetchById, saveDraft, submit, cancel, updateStatus }
})
```

-----

## 12. Sidebar Navigation

```vue
<!-- layouts/DefaultLayout.vue (partial — navigation items) -->
<template>
  <v-app>
    <v-navigation-drawer app permanent>
      <v-list-item
        prepend-icon="mdi-leaf"
        title="GAP Certification"
        subtitle="ระบบรับรองแหล่งผลิต"
      />
      <v-divider />
      <v-list density="compact" nav>
        <v-list-item
          v-for="item in filteredMenuItems"
          :key="item.title"
          :prepend-icon="item.icon"
          :title="item.title"
          :to="item.to"
          link
        />
      </v-list>
    </v-navigation-drawer>

    <v-app-bar app flat>
      <v-spacer />
      <AppNotificationBell />
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" icon>
            <v-avatar color="primary" size="36">
              {{ auth.user?.fullName?.charAt(0) }}
            </v-avatar>
          </v-btn>
        </template>
        <v-list>
          <v-list-item prepend-icon="mdi-account" :title="auth.user?.fullName" />
          <v-list-item prepend-icon="mdi-badge-account" :subtitle="auth.user?.role" />
          <v-divider />
          <v-list-item prepend-icon="mdi-logout" title="ออกจากระบบ" @click="auth.logout()" />
        </v-list>
      </v-menu>
    </v-app-bar>

    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth.store'
import { usePermission } from '@/composables/usePermission'
import AppNotificationBell from '@/components/common/AppNotificationBell.vue'

const auth = useAuthStore()
const { hasRole } = usePermission()

const menuItems = [
  { title: 'Dashboard',        icon: 'mdi-view-dashboard',    to: '/',                roles: ['ALL'] },
  { title: 'คำขอ GAP',         icon: 'mdi-file-document-edit', to: '/applications',   roles: ['ALL'] },
  { title: 'ยื่นคำขอใหม่',       icon: 'mdi-plus-circle',       to: '/applications/new', roles: ['FARMER', 'GROUP_ADMIN'] },
  { title: 'ตรวจประเมิน',       icon: 'mdi-clipboard-check',   to: '/inspections',     roles: ['staff', 'INSPECTOR', 'ADMIN'] },
  { title: 'ใบรับรอง',          icon: 'mdi-certificate',        to: '/certificates',    roles: ['ALL'] },
  { title: 'จัดการผู้ใช้',        icon: 'mdi-account-cog',       to: '/admin/users',     roles: ['ADMIN'] },
  { title: 'ตั้งค่าระบบ',        icon: 'mdi-cog',               to: '/admin/settings',  roles: ['ADMIN'] },
]

const filteredMenuItems = computed(() =>
  menuItems.filter(i => i.roles.includes('ALL') || hasRole(i.roles))
)
</script>
```

-----

## 13. Vuetify Theme Configuration

```typescript
// plugins/vuetify.ts
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'gapTheme',
    themes: {
      gapTheme: {
        dark: false,
        colors: {
          primary:    '#2E7D32',   // เขียวเกษตร
          secondary:  '#FF8F00',   // เหลืองทอง
          accent:     '#00ACC1',
          success:    '#43A047',
          warning:    '#FB8C00',
          error:      '#E53935',
          info:       '#1E88E5',
          background: '#F5F5F5',
          surface:    '#FFFFFF',
        },
      },
    },
  },
  defaults: {
    VBtn:       { rounded: 'lg' },
    VCard:      { rounded: 'lg', elevation: 2 },
    VTextField: { variant: 'outlined', density: 'comfortable' },
    VSelect:    { variant: 'outlined', density: 'comfortable' },
  },
})
```

-----

## 14. API Endpoints Summary

|Method |Endpoint                  |Description                         |Roles                    |
|-------|--------------------------|------------------------------------|-------------------------|
|`POST` |`/auth/token`             |Exchange SSO code for token         |Public                   |
|`GET`  |`/auth/me`                |Get current user profile            |All                      |
|`GET`  |`/applications`           |List applications (filtered by role)|All                      |
|`GET`  |`/applications/summary`   |Dashboard summary counts            |All                      |
|`POST` |`/applications`           |Create new application              |Farmer, GroupAdmin       |
|`GET`  |`/applications/:id`       |Get application detail              |All                      |
|`PUT`  |`/applications/:id`       |Update application                  |Farmer, GroupAdmin       |
|`PATCH`|`/applications/:id/status`|Update status                       |staff, Admin           |
|`GET`  |`/inspections`            |List inspections                    |staff, Inspector, Admin|
|`POST` |`/inspections`            |Schedule inspection                 |staff, Admin           |
|`PUT`  |`/inspections/:id`        |Record inspection result            |Inspector, Admin         |
|`POST` |`/inspections/:id/photos` |Upload inspection photos            |Inspector                |
|`GET`  |`/certificates`           |List certificates                   |All                      |
|`GET`  |`/certificates/:id`       |Get certificate detail              |All                      |
|`POST` |`/certificates`           |Issue certificate                   |staff, Admin           |
|`GET`  |`/certificates/:id/pdf`   |Download certificate PDF            |All                      |
|`GET`  |`/users`                  |List users                          |Admin                    |
|`POST` |`/users`                  |Create user                         |Admin                    |
|`PUT`  |`/users/:id`              |Update user                         |Admin                    |
|`GET`  |`/notifications`          |Get notifications                   |All                      |

-----

## 15. Environment Variables

```env
# .env
VITE_API_BASE_URL=https://api.gap-cert.example.com
VITE_SSO_URL=https://sso.example.com
VITE_SSO_CLIENT_ID=gap-cert-web
VITE_SSO_REDIRECT_URI=http://localhost:3000/auth/callback
VITE_APP_TITLE=ระบบรับรองแหล่งผลิต GAP พืช
```

-----

## 16. Deployment & DevOps Notes

|Concern     |Recommendation                      |
|------------|------------------------------------|
|Build       |`vite build` → static SPA in `dist/`|
|Hosting     |Nginx / CloudFront + S3             |
|SPA Fallback|`try_files $uri $uri/ /index.html`  |
|HTTPS       |Required for SSO redirect           |
|Docker      |Multi-stage build (Node → Nginx)    |
|CI/CD       |GitHub Actions / GitLab CI          |
|Linting     |ESLint + Prettier + vue-tsc         |
|Testing     |Vitest (unit) + Cypress (E2E)       |