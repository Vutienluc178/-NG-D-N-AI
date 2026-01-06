import { PrintClient } from "@/app/print/PrintClient";
import { Suspense } from "react";

export default function PrintPage() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-5xl px-4 py-10 text-sm text-zinc-600">
          Đang tải...
        </div>
      }
    >
      <PrintClient />
    </Suspense>
  );
}

