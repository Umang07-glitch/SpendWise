import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
const variants = cva("inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:pointer-events-none disabled:opacity-50", {variants:{variant:{default:"bg-primary text-white hover:bg-emerald-700",outline:"border border-slate-200 bg-white hover:bg-slate-50 text-slate-700",ghost:"hover:bg-slate-100 text-slate-500",destructive:"bg-red-50 text-red-700 hover:bg-red-100"},size:{default:"h-11 px-4",sm:"h-9 px-3",icon:"h-9 w-9"}},defaultVariants:{variant:"default",size:"default"}});
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof variants> { asChild?: boolean }
export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({className,variant,size,asChild=false,...props},ref)=>{const Comp=asChild?Slot:"button";return <Comp className={cn(variants({variant,size,className}))} ref={ref} {...props}/>;});
Button.displayName="Button";
