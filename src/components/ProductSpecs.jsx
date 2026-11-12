import React from 'react';
import {Activity, Bluetooth, Box, Cable, CircuitBoard, Cpu, Disc, Droplets, Fan, Gauge, Gpu, HardDrive, Layers, Maximize, MemoryStick, Microchip, Monitor, RefreshCw, Ruler, Snowflake, Timer, Usb, Wind, Wifi, Zap} from 'lucide-react';

// Chỉ hiển thị thông số có thật trong specs của sản phẩm; trường trống thì bỏ qua.
const has = v => v !== null && v !== undefined && v !== '' && !(Array.isArray(v) && !v.length);
const num = v => {const n = Number(v); return Number.isFinite(n) ? n : null;};
const fmt = v => {const n = num(v); return n === null ? String(v).trim() : n.toLocaleString('vi-VN', {maximumFractionDigits:1});};
const capacity = gb => {const n = num(gb); if (n === null) return null; return n >= 1000 ? `${fmt(n / 1000)} TB` : `${fmt(n)} GB`;};
// Dữ liệu nhập được chuẩn hóa về chữ thường (nvme/sata); hiển thị lại đúng cách viết.
const iface = v => ({nvme:'NVMe', sata:'SATA'})[String(v).toLowerCase()] || v;
const yesNo = v => v === true ? 'Có' : v === false ? 'Không' : v;
const CONNECT = {Wired:'Có dây', Wireless:'Không dây', Bluetooth:'Bluetooth'};
const TYPE_BY_CAT = {vga:'gpu', 'nguồn':'psu', 'tản nhiệt':'cooler', 'thiết bị ngoại vi':'', 'bản quyền':'license'};

function typeOf(product) {
 if (product.product_type) return product.product_type;
 const cat = String(product.cat || '').trim().toLowerCase();
 return TYPE_BY_CAT[cat] ?? cat;
}

/** Thông số chủ chốt theo loại linh kiện: [{Icon, label, text}], tối đa `limit`. */
export function keySpecs(product, limit = 4) {
 const s = product?.specs || {};
 const out = [];
 const add = (Icon, label, text, ...needed) => {if (needed.every(has)) out.push({Icon, label, text});};
 switch (typeOf(product)) {
  case 'cpu':
   add(Microchip, 'Socket', s.socket, s.socket);
   add(Cpu, 'Nhân / luồng', `${s.cores} nhân / ${s.threads} luồng`, s.cores, s.threads);
   add(Gauge, 'Xung tối đa', `${fmt(s.boost_ghz ?? s.base_ghz)} GHz`, s.boost_ghz ?? s.base_ghz);
   add(Zap, 'TDP', `${fmt(s.tdp_w)} W`, s.tdp_w);
   if (typeof s.has_igpu === 'boolean') add(Monitor, 'Đồ họa tích hợp', yesNo(s.has_igpu), true);
   if (typeof s.stock_cooler === 'boolean') add(Fan, 'Tản nhiệt kèm theo', yesNo(s.stock_cooler), true);
   break;
  case 'gpu':
   add(Gpu, 'Chip đồ họa', s.chip, s.chip);
   add(MemoryStick, 'VRAM', `${fmt(s.vram_gb)} GB`, s.vram_gb);
   add(Zap, 'Công suất', `${fmt(s.tdp_w)} W`, s.tdp_w);
   add(Ruler, 'Chiều dài', `${fmt(s.length_mm)} mm`, s.length_mm);
   break;
  case 'mainboard':
   add(Microchip, 'Socket', s.socket, s.socket);
   add(CircuitBoard, 'Chipset', s.chipset, s.chipset);
   add(MemoryStick, 'Loại RAM', has(s.ram_slots) ? `${s.ram_type} · ${s.ram_slots} khe` : s.ram_type, s.ram_type);
   add(Box, 'Kích thước', s.form_factor, s.form_factor);
   add(Layers, 'RAM tối đa', `${fmt(s.max_ram_gb)} GB`, s.max_ram_gb);
   add(HardDrive, 'Khe M.2', `${s.m2_slots} khe`, s.m2_slots);
   break;
  case 'ram':
   add(MemoryStick, 'Dung lượng', has(s.modules) && num(s.modules) > 1 ? `${fmt(s.capacity_gb)} GB (${s.modules} x ${fmt(num(s.capacity_gb) / num(s.modules))} GB)` : `${fmt(s.capacity_gb)} GB`, s.capacity_gb);
   add(Layers, 'Loại RAM', s.ram_type, s.ram_type);
   add(Gauge, 'Bus', `${fmt(s.speed_mhz)} MHz`, s.speed_mhz);
   add(Timer, 'Độ trễ', `CL${s.cas_latency}`, s.cas_latency);
   break;
  case 'ssd':
   add(HardDrive, 'Dung lượng', capacity(s.capacity_gb), s.capacity_gb);
   add(Activity, 'Giao tiếp', has(s.pcie_gen) ? `${iface(s.interface)} PCIe ${s.pcie_gen}.0` : iface(s.interface), s.interface);
   add(Box, 'Kích thước', s.form_factor, s.form_factor);
   break;
  case 'hdd':
   add(HardDrive, 'Dung lượng', capacity(s.capacity_gb), s.capacity_gb);
   add(Disc, 'Tốc độ quay', `${fmt(s.rpm)} RPM`, s.rpm);
   add(Box, 'Kích thước', s.form_factor, s.form_factor);
   break;
  case 'psu':
   add(Zap, 'Công suất', `${fmt(s.watt)} W`, s.watt);
   add(Gauge, 'Chuẩn hiệu suất', String(s.efficiency || '').trim().replace(/^80\+$/, '80 Plus'), String(s.efficiency || '').trim());
   if (typeof s.modular === 'boolean') add(Cable, 'Dây cáp', s.modular ? 'Full modular' : 'Dây liền', true);
   break;
  case 'case':
   add(Box, 'Loại vỏ', s.form_factor, s.form_factor);
   add(Gpu, 'VGA dài tối đa', `${fmt(s.max_gpu_length_mm)} mm`, s.max_gpu_length_mm);
   add(Fan, 'Tản khí cao tối đa', `${fmt(s.max_cooler_height_mm)} mm`, s.max_cooler_height_mm);
   add(CircuitBoard, 'Mainboard hỗ trợ', Array.isArray(s.supported_mb) ? s.supported_mb.join(', ') : s.supported_mb, s.supported_mb);
   break;
  case 'cooler':
   if (s.cooler_type === 'liquid') add(Droplets, 'Loại tản', has(s.radiator_mm) ? `Tản nước ${fmt(s.radiator_mm)} mm` : 'Tản nước', true);
   else if (s.cooler_type === 'air') add(Snowflake, 'Loại tản', 'Tản khí', true);
   add(Wind, 'Lưu lượng gió', `${fmt(s.airflow_cfm)} CFM`, s.airflow_cfm);
   add(Ruler, 'Chiều cao', `${fmt(s.height_mm)} mm`, s.height_mm);
   if (Array.isArray(s.sockets) && s.sockets.length) add(Microchip, 'Socket hỗ trợ', s.sockets.slice(0, 3).join(', ') + (s.sockets.length > 3 ? ` +${s.sockets.length - 3}` : ''), true);
   break;
  case 'fan':
   add(Fan, 'Kích thước quạt', `${fmt(s.diameter_mm)} mm`, s.diameter_mm);
   add(Wind, 'Lưu lượng gió', `${fmt(s.airflow_cfm)} CFM`, s.airflow_cfm);
   add(Layers, 'Số quạt', `Bộ ${s.pack_quantity} quạt`, s.pack_quantity);
   break;
  case 'monitor':
   add(Monitor, 'Kích thước', `${fmt(s.diagonal_inches)} inch`, s.diagonal_inches);
   add(RefreshCw, 'Tần số quét', `${fmt(s.refresh_hz)} Hz`, s.refresh_hz);
   add(Maximize, 'Độ phân giải', s.resolution, s.resolution);
   break;
  case 'mouse': case 'keyboard': case 'headphones':
   (Array.isArray(s.connectivity) ? s.connectivity : []).forEach(c => add(c === 'Bluetooth' ? Bluetooth : c === 'Wireless' ? Wifi : Usb, 'Kết nối', CONNECT[c] || c, c));
   break;
  default:
 }
 return out.slice(0, limit);
}

// Nhãn tiếng Việt + định dạng cho bảng thông số đầy đủ.
const SPEC_FIELDS = {
 socket:['Socket'], chipset:['Chipset'], cores:['Số nhân'], threads:['Số luồng'],
 base_ghz:['Xung cơ bản', v => `${fmt(v)} GHz`], boost_ghz:['Xung tối đa', v => `${fmt(v)} GHz`],
 tdp_w:['Công suất / TDP', v => `${fmt(v)} W`], has_igpu:['Đồ họa tích hợp', yesNo], stock_cooler:['Tản nhiệt kèm theo', yesNo],
 chip:['Chip đồ họa'], vram_gb:['VRAM', v => `${fmt(v)} GB`], length_mm:['Chiều dài', v => `${fmt(v)} mm`],
 form_factor:['Kích thước / chuẩn'], ram_type:['Loại RAM'], ram_slots:['Số khe RAM'], max_ram_gb:['RAM tối đa', v => `${fmt(v)} GB`], m2_slots:['Số khe M.2'],
 capacity_gb:['Dung lượng', v => capacity(v)], modules:['Số thanh'], speed_mhz:['Bus', v => `${fmt(v)} MHz`], cas_latency:['Độ trễ', v => `CL${v}`],
 interface:['Giao tiếp', iface], pcie_gen:['Thế hệ PCIe', v => `PCIe ${v}.0`], rpm:['Tốc độ quay', v => `${fmt(v)} RPM`],
 watt:['Công suất', v => `${fmt(v)} W`], efficiency:['Chuẩn hiệu suất', v => String(v).trim()], modular:['Modular', v => v ? 'Full modular' : 'Dây liền'],
 supported_mb:['Mainboard hỗ trợ'], max_gpu_length_mm:['VGA dài tối đa', v => `${fmt(v)} mm`], max_cooler_height_mm:['Tản khí cao tối đa', v => `${fmt(v)} mm`],
 cooler_type:['Loại tản nhiệt', v => v === 'liquid' ? 'Tản nước' : v === 'air' ? 'Tản khí' : v], radiator_mm:['Radiator', v => `${fmt(v)} mm`],
 airflow_cfm:['Lưu lượng gió', v => `${fmt(v)} CFM`], height_mm:['Chiều cao', v => `${fmt(v)} mm`], sockets:['Socket hỗ trợ'],
 diameter_mm:['Kích thước quạt', v => `${fmt(v)} mm`], pack_quantity:['Số quạt / bộ'],
 diagonal_inches:['Kích thước màn hình', v => `${fmt(v)} inch`], refresh_hz:['Tần số quét', v => `${fmt(v)} Hz`], resolution:['Độ phân giải'],
 connectivity:['Kết nối', v => (Array.isArray(v) ? v : [v]).map(c => CONNECT[c] || c).join(', ')],
};

/** Bảng thông số: ưu tiên specs có cấu trúc; nếu không có thì dùng thuộc tính admin nhập. */
export function specRows(product) {
 const specs = product?.specs || {};
 // Sắp theo thứ tự khai báo trong SPEC_FIELDS (socket, nhân, luồng, xung…), trường lạ để cuối.
 const order = Object.keys(SPEC_FIELDS);
 const rank = k => (order.indexOf(k) + 1) || order.length + 1;
 const rows = Object.entries(specs).filter(([, v]) => has(v)).sort(([a], [b]) => rank(a) - rank(b)).map(([key, v]) => {
  const [label, format] = SPEC_FIELDS[key] || [key];
  const value = format ? format(v) : Array.isArray(v) ? v.join(', ') : v;
  return {label, value: String(value)};
 });
 if (rows.length) return rows;
 return (product?.attributes || []).filter(a => a?.name && has(a.value))
  .map(a => ({label:a.name, value:`${Array.isArray(a.value) ? a.value.join(', ') : a.value}${a.unit ? ` ${a.unit}` : ''}`}));
}

export default function ProductSpecs({product, className = ''}) {
 const specs = keySpecs(product);
 if (!specs.length) return <div className={`spec-box spec-box-empty ${className}`} aria-hidden="true"/>;
 return <ul className={`spec-box ${className}`} aria-label="Cấu hình chính">
  {specs.map(({Icon, text}) => <li key={text}><Icon aria-hidden="true"/><span>{text}</span></li>)}
 </ul>;
}
