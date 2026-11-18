// Keep composer menus inside the visible viewport, including the mobile keyboard.
export const vPopoverPlacement = {
  mounted(el, { value: within }) {
    let frame
    const place = () => {
      const anchor = el.parentElement
      if (!anchor || !el.isConnected) return
      const viewport = window.visualViewport
      const viewportTop = viewport?.offsetTop || 0
      const viewportLeft = viewport?.offsetLeft || 0
      const boundsLimit = within && el.closest(within)?.getBoundingClientRect()
      const top = Math.max(viewportTop, boundsLimit?.top ?? -Infinity)
      const left = Math.max(viewportLeft, boundsLimit?.left ?? -Infinity)
      const bottom = Math.min(viewportTop + (viewport?.height || window.innerHeight), boundsLimit?.bottom ?? Infinity)
      const right = Math.min(viewportLeft + (viewport?.width || window.innerWidth), boundsLimit?.right ?? Infinity)
      const gap = 8
      el.style.maxHeight = ''
      el.style.maxWidth = ''
      el.style.left = ''
      el.style.right = ''
      const css = getComputedStyle(el)
      const limit = parseFloat(css.maxHeight) || 440
      el.style.maxWidth = `${Math.min(parseFloat(css.maxWidth) || Infinity, Math.max(0, right - left - gap * 2))}px`
      const bounds = anchor.getBoundingClientRect()
      const above = Math.max(0, bounds.top - top - gap * 2)
      const below = Math.max(0, bottom - bounds.bottom - gap * 2)
      const up = Boolean(el.closest('.has-session')) || (below < Math.min(limit, el.scrollHeight + 2) && above > below)
      el.dataset.placement = up ? 'top' : 'bottom'
      el.style.top = up ? 'auto' : `calc(100% + ${gap}px)`
      el.style.bottom = up ? `calc(100% + ${gap}px)` : 'auto'
      el.style.maxHeight = `${Math.min(limit, up ? above : below)}px`
      const menu = el.getBoundingClientRect()
      const x = Math.max(left + gap, Math.min(menu.left, right - menu.width - gap))
      el.style.left = `${x - bounds.left}px`
      el.style.right = 'auto'
    }
    const schedule = () => { cancelAnimationFrame(frame); frame = requestAnimationFrame(place) }
    const observer = new ResizeObserver(schedule)
    observer.observe(el)
    window.addEventListener('resize', schedule)
    window.addEventListener('scroll', schedule, true)
    window.visualViewport?.addEventListener('resize', schedule)
    window.visualViewport?.addEventListener('scroll', schedule)
    el.__popoverCleanup = () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
      window.removeEventListener('resize', schedule)
      window.removeEventListener('scroll', schedule, true)
      window.visualViewport?.removeEventListener('resize', schedule)
      window.visualViewport?.removeEventListener('scroll', schedule)
    }
    place()
  },
  unmounted(el) { el.__popoverCleanup?.() },
}
