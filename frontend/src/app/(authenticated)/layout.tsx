import Sidebar from "@/components/layout/Sidebar";
import AuthGuard from "@/components/layout/AuthGuard";

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="min-h-screen">
        <Sidebar />
        <main className="lg:mr-64 min-h-screen">
          <div className="p-4 pt-16 lg:p-8 lg:pt-8">{children}</div>
        </main>
      </div>
    </AuthGuard>
  );
}
