"use client";

// Redirect to dashboard - projects are shown there
import { redirect } from "next/navigation";

export default function ProjectsPage() {
  redirect("/dashboard");
}
