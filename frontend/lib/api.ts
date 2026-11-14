export async function api<T=any>(path:string, options:RequestInit={}, csrf=""):Promise<T>{
 const headers=new Headers(options.headers); if(options.body && !(options.body instanceof FormData)) headers.set("Content-Type","application/json");
 if(csrf) headers.set("X-CSRF-Token",csrf);
 const response=await fetch(`/api${path}`,{...options,headers,credentials:"include",cache:"no-store"});
 if(!response.ok){const data=await response.json().catch(()=>({})); throw new Error(typeof data.detail==="string"?data.detail:Array.isArray(data.detail)?data.detail.map((d:any)=>`${d.loc.slice(1).join(".")}: ${d.msg}`).join("; "):"Request failed. Please try again.");}
 return response.status===204?undefined:response.json();
}
export const categories=["Salary","Freelance","Food & Dining","Shopping","Transport","Housing","Utilities","Entertainment","Health","Education","Travel","Other"];
export type Transaction={id:number;title:string;amount:string;kind:"income"|"expense";category:string;date:string;notes:string};
export type User={id:number;name:string;email:string;currency:string;notifications:boolean};
