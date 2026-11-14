import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata={title:"SpendWise · Your money, in perspective",description:"Your personal finance workspace. Track spending, build budgets and plan ahead."};
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="en"><body>{children}</body></html>;}
