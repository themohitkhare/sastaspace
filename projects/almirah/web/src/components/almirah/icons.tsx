import type { ReactNode } from "react";

function Icon({
  children,
  size = 20,
  stroke = 1.75,
}: {
  children: ReactNode;
  size?: number;
  stroke?: number;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

export const IconRack = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M3 6h18M6 6v13M18 6v13M3 19h18M8 10h2M14 10h2M11 14h2" />
  </Icon>
);

export const IconToday = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
  </Icon>
);

export const IconPlan = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <rect x="3" y="5" width="18" height="16" rx="2" />
    <path d="M8 3v4M16 3v4M3 10h18" />
  </Icon>
);

export const IconMe = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="12" cy="8" r="4" />
    <path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8" />
  </Icon>
);

export const IconSearch = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="11" cy="11" r="7" />
    <path d="m20 20-3.5-3.5" />
  </Icon>
);

export const IconPlus = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
);

export const IconBack = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M15 18l-6-6 6-6" />
  </Icon>
);

export const IconClose = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Icon>
);

export const IconCheck = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M5 12l5 5 9-11" />
  </Icon>
);

export const IconMore = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <circle cx="5" cy="12" r="1.5" />
    <circle cx="12" cy="12" r="1.5" />
    <circle cx="19" cy="12" r="1.5" />
  </Icon>
);

export const IconCamera = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M4 8h3l2-3h6l2 3h3a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2v-9a2 2 0 0 1 2-2z" />
    <circle cx="12" cy="13" r="4" />
  </Icon>
);

export const IconUpload = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M12 16V4M6 10l6-6 6 6M4 20h16" />
  </Icon>
);

export const IconSparkle = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M12 3l2.5 5.5L20 11l-5.5 2.5L12 19l-2.5-5.5L4 11l5.5-2.5z" />
  </Icon>
);

export const IconExternal = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M14 5h5v5M19 5L10 14M12 5H7a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" />
  </Icon>
);

export const IconWand = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M4 20l12-12M14 4l2 2M18 8l2 2M8 14l2 2" />
  </Icon>
);

export const IconArrow = ({ size = 20 }: { size?: number }) => (
  <Icon size={size}>
    <path d="M5 12h14M13 5l7 7-7 7" />
  </Icon>
);
