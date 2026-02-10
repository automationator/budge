import { beforeAll, afterAll, afterEach, vi } from 'vitest'
import { config } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { createTestingPinia } from '@pinia/testing'
import { server } from './mocks/server'

// Mock vue-router to avoid history state issues in happy-dom
// Create shared mock instances so they can be accessed in tests
const mockRouterInstance = {
  push: vi.fn(),
  replace: vi.fn(),
  go: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  beforeEach: vi.fn(),
  afterEach: vi.fn(),
  onError: vi.fn(),
  isReady: vi.fn(() => Promise.resolve()),
  install: vi.fn(),
  currentRoute: { value: { path: '/', name: undefined, params: {}, query: {} } },
}

const mockRouteInstance = {
  path: '/',
  name: undefined,
  params: {},
  query: {},
}

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual,
    createRouter: vi.fn(() => mockRouterInstance),
    createWebHistory: vi.fn(() => ({})),
    useRouter: vi.fn(() => mockRouterInstance),
    useRoute: vi.fn(() => mockRouteInstance),
  }
})

// Export for tests that need to access the mock
export { mockRouterInstance, mockRouteInstance }

// Set the base URL for happy-dom so relative URLs resolve correctly
// MSW will intercept these requests
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'location', {
    value: {
      ...window.location,
      href: 'http://localhost:5173',
      origin: 'http://localhost:5173',
      protocol: 'http:',
      host: 'localhost:5173',
      hostname: 'localhost',
      port: '5173',
      pathname: '/',
      search: '',
      hash: '',
    },
    writable: true,
  })
}

// Create Vuetify instance for tests
const vuetify = createVuetify({
  components,
  directives,
})

// Global plugins for Vue Test Utils
config.global.plugins = [vuetify]

// Mock IntersectionObserver (used by Vuetify)
class MockIntersectionObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}
vi.stubGlobal('IntersectionObserver', MockIntersectionObserver)

// Mock ResizeObserver (used by Vuetify)
class MockResizeObserver {
  observe = vi.fn()
  disconnect = vi.fn()
  unobserve = vi.fn()
}
vi.stubGlobal('ResizeObserver', MockResizeObserver)

// Mock visualViewport (used by Vuetify overlay positioning)
vi.stubGlobal('visualViewport', {
  width: 1024,
  height: 768,
  offsetLeft: 0,
  offsetTop: 0,
  pageLeft: 0,
  pageTop: 0,
  scale: 1,
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
})

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  }
})()
vi.stubGlobal('localStorage', localStorageMock)

// MSW server lifecycle
beforeAll(() => server.listen({ onUnhandledRequest: 'warn' }))
afterEach(() => {
  server.resetHandlers()
  localStorageMock.clear()
})
afterAll(() => server.close())

// Export helper to create testing pinia
export function createTestPinia() {
  return createTestingPinia({
    createSpy: vi.fn,
    stubActions: false,
  })
}

// Re-export factories for convenience
export { factories } from './mocks/handlers'
