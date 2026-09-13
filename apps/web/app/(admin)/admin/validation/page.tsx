import { Suspense } from "react";

import { ListSkeleton } from "@/components/admin/shared";
import { ValidationQueue } from "@/components/admin/ValidationQueue";

export default function AdminValidationPage() {
  return (
    <Suspense fallback={<ListSkeleton />}>
      <ValidationQueue />
    </Suspense>
  );
}
