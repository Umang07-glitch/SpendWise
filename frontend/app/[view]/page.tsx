import { notFound } from "next/navigation";
import SpendWise from "@/components/spendwise";
export default async function Page({params}:{params:Promise<{view:string}>}){const {view}=await params;if(!["transactions","budgets","subscriptions","insights","forecast","reports","settings"].includes(view))notFound();return <SpendWise view={view}/>;}
