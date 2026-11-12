// The platform frontend's runtime adapter imports the app's auth module through
// a Vite alias that plain Node cannot resolve; unit tests only need API_BASE.
export async function resolve(specifier, context, next) {
  if (specifier === './runtime' && context.parentURL?.includes('/agent-platform/')) {
    return { url: new URL('./runtime-stub.mjs', import.meta.url).href, shortCircuit: true }
  }
  return next(specifier, context)
}
