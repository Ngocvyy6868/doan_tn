import React, {useState} from 'react';
import {App, Button, Image, Input, Space, Upload} from 'antd';
import {UploadOutlined} from '@ant-design/icons';
const api = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';
export default function ProductImageInput({value, onChange, onUploadingChange}) {
 const {message} = App.useApp();
 const [uploading, setUploading] = useState(false);
 const upload = async file => {
  if (file.size > 5 * 1024 * 1024) { message.error('Ảnh tối đa 5 MB.'); return false; }
  setUploading(true); onUploadingChange(true);
  try {
   const body = new FormData(); body.append('file', file);
   const response = await fetch(`${api}/admin/product-images/`, {method:'POST', credentials:'include', body});
   const data = await response.json();
   if (!response.ok) throw new Error(data.message || 'Không tải được ảnh.');
   onChange(data.url); message.success('Đã tải ảnh. Bấm Lưu để cập nhật sản phẩm.');
  } catch (error) { message.error(error.message || 'Không tải được ảnh.'); }
  finally { setUploading(false); onUploadingChange(false); }
  return false;
 };
 return <Space direction="vertical" style={{width:'100%'}}>
  <Input value={value} onChange={event=>onChange(event.target.value)} placeholder="URL ảnh hoặc tải ảnh từ máy" disabled={uploading}/>
  <Upload accept="image/jpeg,image/png,image/webp" showUploadList={false} beforeUpload={upload} disabled={uploading}>
   <Button icon={<UploadOutlined/>} loading={uploading}>Tải ảnh lên</Button>
  </Upload>
  <span>JPG, PNG, WebP · Tối đa 5 MB</span>
  {value && <Image src={value} width={140} height={110} style={{objectFit:'contain'}}/>}
 </Space>;
}
