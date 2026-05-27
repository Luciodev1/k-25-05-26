/*!
 * Color mode toggler for Bootstrap's docs (https://getbootstrap.com/)
 * Copyright 2011-2023 The Bootstrap Authors
 * Licensed under the Creative Commons Attribution 3.0 Unported License.
 */

(() => {
    'use strict'
  
    const getStoredTheme = () => localStorage.getItem('theme')
    const setStoredTheme = theme => localStorage.setItem('theme', theme)
  
    const getPreferredTheme = () => {
      const storedTheme = getStoredTheme()
      if (storedTheme) {
        return storedTheme
      }
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
  
    const setTheme = theme => {
      if (theme === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        document.documentElement.setAttribute('data-bs-theme', 'dark')
      } else {
        document.documentElement.setAttribute('data-bs-theme', theme)
      }
    }
  
    setTheme(getPreferredTheme())
  
    const showActiveTheme = (theme) => {
      const themeSwitcherBtn = document.querySelector('#bd-theme')
      
      if (!themeSwitcherBtn) {
        return
      }
  
      const themeIconActive = document.querySelector('#bd-theme-icon')
      
      if (theme === 'dark') {
          themeIconActive.classList.remove('bi-sun-fill')
          themeIconActive.classList.add('bi-moon-stars-fill')
      } else {
          themeIconActive.classList.remove('bi-moon-stars-fill')
          themeIconActive.classList.add('bi-sun-fill')
      }
    }
  
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      const storedTheme = getStoredTheme()
      if (storedTheme !== 'light' && storedTheme !== 'dark') {
        setTheme(getPreferredTheme())
      }
    })
  
    window.addEventListener('DOMContentLoaded', () => {
      showActiveTheme(getPreferredTheme())
  
      const toggleThemeBtn = document.querySelector('#bd-theme')
      if (toggleThemeBtn) {
          toggleThemeBtn.addEventListener('click', () => {
              const currentTheme = document.documentElement.getAttribute('data-bs-theme')
              const newTheme = currentTheme === 'dark' ? 'light' : 'dark'
              setStoredTheme(newTheme)
              setTheme(newTheme)
              showActiveTheme(newTheme)
          })
      }
    })
  })()
  
