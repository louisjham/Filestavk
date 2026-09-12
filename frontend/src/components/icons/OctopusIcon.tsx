import React from "react"

interface OctopusIconProps extends React.SVGProps<SVGSVGElement> {
  size?: number
}

export function OctopusIcon({ size = 24, className, ...props }: OctopusIconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      {...props}
    >
      <defs>
        <linearGradient id="hemocyanin-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
          <stop stopColor="#06b6d4" />
          <stop offset="0.5" stopColor="#3b82f6" />
          <stop offset="1" stopColor="#6366f1" />
        </linearGradient>
      </defs>
      
      {/* Stylized Octopus Head / Mantle */}
      <path
        d="M12 2C7.58172 2 4 5.58172 4 10C4 12.8 5.4 15.2 7.5 16.5V17C7.5 17.6 7.9 18 8.5 18H15.5C16.1 18 16.5 17.6 16.5 17V16.5C18.6 15.2 20 12.8 20 10C20 5.58172 16.4183 2 12 2Z"
        fill="url(#hemocyanin-grad)"
        fillOpacity="0.2"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Eyes */}
      <circle cx="9" cy="9.5" r="1.5" fill="#38bdf8" />
      <circle cx="15" cy="9.5" r="1.5" fill="#38bdf8" />

      {/* Elegant Tentacles */}
      <path
        d="M6 15.5C5 17 3.5 18 2.5 17C1.5 16 2.5 14 4.5 14"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M8.5 18C7.5 19.5 6.5 21.5 5 21C3.5 20.5 4.5 18.5 6.5 18"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M11 18C10.5 20 9.5 22 8.5 22C7.5 22 8 20 9 18"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M13 18C13.5 20 14.5 22 15.5 22C16.5 22 16 20 15 18"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M15.5 18C16.5 19.5 17.5 21.5 19 21C20.5 20.5 19.5 18.5 17.5 18"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
      <path
        d="M18 15.5C19 17 20.5 18 21.5 17C22.5 16 21.5 14 19.5 14"
        stroke="url(#hemocyanin-grad)"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  )
}
