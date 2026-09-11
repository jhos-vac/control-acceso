import React from "react";

export default function StatCard({ icon: Icon, label, value, iconBg, iconColor }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-slate-500">{label}</p>
        <div
          className={`w-8 h-8 rounded-lg flex items-center justify-center ${
            iconBg || "bg-brand-50"
          }`}
        >
          <Icon size={16} className={iconColor || "text-brand-600"} />
        </div>
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
    </div>
  );
}
