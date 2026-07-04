import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/text2img',
  },
  {
    path: '/text2img',
    name: 'Text2Img',
    component: () => import('@/views/Text2Img.vue'),
    meta: { title: 'Text to Image' },
  },
  {
    path: '/img2img',
    name: 'Img2Img',
    component: () => import('@/views/Img2Img.vue'),
    meta: { title: 'Image to Image' },
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/History.vue'),
    meta: { title: 'History' },
  },
  {
    path: '/prompts',
    name: 'Prompts',
    component: () => import('@/views/Prompts.vue'),
    meta: { title: 'Prompt Manager' },
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('@/views/Models.vue'),
    meta: { title: 'Model Manager' },
  },
  {
    path: '/browser',
    name: 'Browser',
    component: () => import('@/views/Browser.vue'),
    meta: { title: 'Image Browser' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/Settings.vue'),
    meta: { title: 'Settings' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
