import React from 'react';
import {Activity, Bluetooth, Box, Cable, CircuitBoard, Cpu, Disc, Droplets, Fan, Gauge, Gpu, HardDrive, Layers, Maximize, MemoryStick, Microchip, Monitor, RefreshCw, Ruler, Snowflake, Timer, Usb, Wind, Wifi, Zap} from 'lucide-react';

// Chỉ hiển thị thông số có thật trong specs của sản phẩm; trường trống thì bỏ qua.
const has = v => v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && !v.length);
const num = v => {const n = Number(v); return Number.isFinite(n) ? n : null;};
const fmt = v => {const n = num(v); return n === null ? String(v).trim() : n.toLocaleString('vi-VN', {maximumFractionDigits:1});};
const capacity = gb => {const n = num(gb); if (n === null) return null; return n >= 1000 ? `${fmt(n / 1000)} TB` : `${fmt(n)} GB`;};
const CONNECT = {Wired:'Có dây', Wireless:'Không dây', Bluetooth:'Bluetooth'};
const TYPE_BY_CAT = {vga:'gpu', 'nguồn':'psu', 'tản nhiệt':'cooler', 'thiết bị ngoại vi':'', 'bản quyền':'license'};

function typeOf(product) {
 if (product.product_type) return product.product_type;
 const cat = String(product.cat || '').trim().toLowerCase();
 return TYPE_BY_CAT[cat] ?? cat;
}

export function keySpecs(product) {
 const s = product?.specs || {};
 const out = [];
 const add = (Icon, text, ...needed) => {if (needed.every(has)) out.push({Icon, text});};
 switch (typeOf(product)) {
  case 'cpu':
   add(Microchip, `Socket ${s.socket}`, s.socket);
   add(Cpu, `${s.cores} nhân / ${s.threads} luồng`, s.cores, s.threads);
   add(Gauge, `${fmt(s.boost_ghz ?? s.base_ghz)} GHz`, s.boost_ghz ?? s.base_ghz);
   add(Zap, `${fmt(s.tdp_w)} W`, s.tdp_w);
   break;
  case 'gpu':
   add(Gpu, s.chip, s.chip);
   add(MemoryStick, `${fmt(s.vram_gb)} GB VRAM`, s.vram_gb);
   add(Zap, `${fmt(s.tdp_w)} W`, s.tdp_w);
   add(Ruler, `${fmt(s.length_mm)} mm`, s.length_mm);
   break;
  case 'mainboard':
   add(Microchip, `Socket ${s.socket}`, s.socket);
   add(CircuitBoard, s.chipset, s.chipset);
   add(MemoryStick, has(s.ram_slots) ? `${s.ram_type} · ${s.ram_slots} khe` : s.ram_type, s.ram_type);
   add(Box, s.form_factor, s.form_factor);
   break;
  case 'ram':
   add(MemoryStick, has(s.modules) && num(s.modules) > 1 ? `${fmt(s.capacity_gb)} GB (${s.modules} x ${fmt(num(s.capacity_gb) / num(s.modules))} GB)` : `${fmt(s.capacity_gb)} GB`, s.capacity_gb);
   add(Layers, s.ram_type, s.ram_type);
   add(Gauge, `${fmt(s.speed_mhz)} MHz`, s.speed_mhz);
   add(Timer, `CL${s.cas_latency}`, s.cas_latency);
   break;
  case 'ssd':
   add(HardDrive, capacity(s.capacity_gb), s.capacity_gb);
   add(Activity, has(s.pcie_gen) ? `${s.interface} PCIe ${s.pcie_gen}.0` : s.interface, s.interface);
   add(Box, s.form_factor, s.form_factor);
   break;
  case 'hdd':
   add(HardDrive, capacity(s.capacity_gb), s.capacity_gb);
   add(Disc, `${fmt(s.rpm)} RPM`, s.rpm);
   add(Box, s.form_factor, s.form_factor);
   break;
  case 'psu':
   add(Zap, `${fmt(s.watt)} W`, s.watt);
   add(Gauge, String(s.efficiency || '').trim().replace(/^80\+$/, '80 Plus'), String(s.efficiency || '').trim());
   if (typeof s.modular === 'boolean') add(Cable, s.modular ? 'Full modular' : 'Dây liền', true);
   break;
  case 'case':
   add(Box, s.form_factor, s.form_factor);
   add(Gpu, `VGA tối đa ${fmt(s.max_gpu_length_mm)} mm`, s.max_gpu_length_mm);
   add(Fan, `Tản khí tối đa ${fmt(s.max_cooler_height_mm)} mm`, s.max_cooler_height_mm);
   break;
  case 'cooler':
   if (s.cooler_type === 'liquid') add(Droplets, has(s.radiator_mm) ? `Tản nước ${fmt(s.radiator_mm)} mm` : 'Tản nước', true);
   else if (s.cooler_type === 'air') add(Snowflake, 'Tản khí', true);
   add(Wind, `${fmt(s.airflow_cfm)} CFM`, s.airflow_cfm);
   add(Ruler, `Cao ${fmt(s.height_mm)} mm`, s.height_mm);
   if (Array.isArray(s.sockets) && s.sockets.length) add(Microchip, s.sockets.slice(0, 3).join(', ') + (s.sockets.length > 3 ? ` +${s.sockets.length - 3}` : ''), true);
   break;
  case 'fan':
   add(Fan, `${fmt(s.diameter_mm)} mm`, s.diameter_mm);
   add(Wind, `${fmt(s.airflow_cfm)} CFM`, s.airflow_cfm);
   add(Layers, `Bộ ${s.pack_quantity} quạt`, s.pack_quantity);
   break;
  case 'monitor':
   add(Monitor, `${fmt(s.diagonal_inches)} inch`, s.diagonal_inches);
   add(RefreshCw, `${fmt(s.refresh_hz)} Hz`, s.refresh_hz);
   add(Maximize, s.resolution, s.resolution);
   break;
  case 'mouse': case 'keyboard': case 'headphones':
   (Array.isArray(s.connectivity) ? s.connectivity : []).forEach(c => add(c === 'Bluetooth' ? Bluetooth : c === 'Wireless' ? Wifi : Usb, CONNECT[c] || c, c));
   break;
  default:
 }
 return out.slice(0, 4);
}

export default function ProductSpecs({product, className = ''}) {
 const specs = keySpecs(product);
 if (!specs.length) return <div className={`spec-box spec-box-empty ${className}`} aria-hidden="true"/>;
 return <ul className={`spec-box ${className}`} aria-label="Cấu hình chính">
  {specs.map(({Icon, text}) => <li key={text}><Icon aria-hidden="true"/><span>{text}</span></li>)}
 </ul>;
}
