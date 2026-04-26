'use client';

import { SastaspaceProvider } from '@/hooks/useStdb';
import Shell from '@/components/Shell';

export default function Page() {
  return (
    <SastaspaceProvider>
      <Shell/>
    </SastaspaceProvider>
  );
}
