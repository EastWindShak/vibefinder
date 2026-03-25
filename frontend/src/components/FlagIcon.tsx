interface FlagIconProps {
  code: string
  className?: string
}

export default function FlagIcon({ code, className = "w-5 h-4" }: FlagIconProps) {
  const flags: Record<string, JSX.Element> = {
    en: (
      // UK Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="40" fill="#012169"/>
        <path d="M0 0L60 40M60 0L0 40" stroke="white" strokeWidth="8"/>
        <path d="M0 0L60 40M60 0L0 40" stroke="#C8102E" strokeWidth="4"/>
        <path d="M30 0V40M0 20H60" stroke="white" strokeWidth="12"/>
        <path d="M30 0V40M0 20H60" stroke="#C8102E" strokeWidth="6"/>
      </svg>
    ),
    de: (
      // Germany Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="13.33" fill="#000000"/>
        <rect y="13.33" width="60" height="13.33" fill="#DD0000"/>
        <rect y="26.67" width="60" height="13.33" fill="#FFCC00"/>
      </svg>
    ),
    es: (
      // Spain Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="40" fill="#FFCC00"/>
        <rect width="60" height="10" fill="#C60B1E"/>
        <rect y="30" width="60" height="10" fill="#C60B1E"/>
      </svg>
    ),
    fr: (
      // France Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="20" height="40" fill="#002395"/>
        <rect x="20" width="20" height="40" fill="#FFFFFF"/>
        <rect x="40" width="20" height="40" fill="#ED2939"/>
      </svg>
    ),
    it: (
      // Italy Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="20" height="40" fill="#009246"/>
        <rect x="20" width="20" height="40" fill="#FFFFFF"/>
        <rect x="40" width="20" height="40" fill="#CE2B37"/>
      </svg>
    ),
    hi: (
      // India Flag
      <svg className={className} viewBox="0 0 60 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="13.33" fill="#FF9933"/>
        <rect y="13.33" width="60" height="13.33" fill="#FFFFFF"/>
        <rect y="26.67" width="60" height="13.33" fill="#138808"/>
        <circle cx="30" cy="20" r="4" fill="#000080"/>
        <circle cx="30" cy="20" r="3.2" fill="#FFFFFF"/>
        <circle cx="30" cy="20" r="1" fill="#000080"/>
      </svg>
    ),
  }

  return (
    <span className="inline-flex items-center justify-center rounded overflow-hidden shadow-sm border border-neutral-200">
      {flags[code] || null}
    </span>
  )
}
