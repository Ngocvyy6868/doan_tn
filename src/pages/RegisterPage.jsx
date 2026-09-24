import { useState } from 'react';
import { Alert, Button, Card, Checkbox, Form, Input, Result, Typography } from 'antd';
import { LockOutlined, MailOutlined, UserOutlined } from '@ant-design/icons';
import './RegisterPage.css';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function RegisterPage() {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const [completed, setCompleted] = useState(false);
  const submit = async (values) => {
    setSubmitting(true); setApiError('');
    try {
      const response = await fetch(`${apiBaseUrl}/auth/register/`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ full_name: values.full_name, email: values.email, phone: values.phone, password: values.password, password_confirmation: values.password_confirmation }) });
      const data = await response.json();
      if (!response.ok) { Object.entries(data.errors || {}).forEach(([field, message]) => form.setFields([{ name: field, errors: [Array.isArray(message) ? message.join(' ') : message] }])); setApiError(data.message || 'Không thể đăng ký tài khoản.'); return; }
      localStorage.setItem('techzone_user', JSON.stringify(data.user));
      window.location.assign('/');
    } catch { setApiError('Không thể kết nối máy chủ. Vui lòng thử lại sau.'); } finally { setSubmitting(false); }
  };
  return <main className="register-page"><Card className="register-card" bordered={false}>{completed ? <Result status="success" title="Đăng ký thành công" subTitle="Tài khoản của bạn đã được tạo. Bạn có thể đăng nhập để tiếp tục mua sắm." extra={<Button type="primary" href="/">Về trang chủ</Button>} /> : <><div className="register-heading"><a href="/" className="register-logo">TZ</a><Typography.Title level={2}>Tạo tài khoản</Typography.Title><Typography.Text>Đăng ký để theo dõi đơn hàng và nhận ưu đãi từ TechZone.</Typography.Text></div>{apiError && <Alert type="error" showIcon message={apiError} className="register-alert" />}<Form form={form} layout="vertical" onFinish={submit} requiredMark={false}><Form.Item name="full_name" label="Họ và tên" rules={[{ required: true, message: 'Vui lòng nhập họ và tên.' }]}><Input prefix={<UserOutlined />} autoComplete="name" placeholder="Nguyễn Văn A" size="large" /></Form.Item><Form.Item name="email" label="Email" rules={[{ required: true, message: 'Vui lòng nhập email.' }, { type: 'email', message: 'Email không hợp lệ.' }]}><Input prefix={<MailOutlined />} autoComplete="email" placeholder="email@domain.com" size="large" /></Form.Item><Form.Item name="phone" label="Số điện thoại" rules={[{ required: true, message: 'Vui lòng nhập số điện thoại.' }, { pattern: /^(0|\+84)\d{9}$/, message: 'Số điện thoại không hợp lệ.' }]}><Input autoComplete="tel" placeholder="0901234567" size="large" /></Form.Item><Form.Item name="password" label="Mật khẩu" rules={[{ required: true, message: 'Vui lòng nhập mật khẩu.' }, { min: 8, message: 'Mật khẩu phải có ít nhất 8 ký tự.' }]}><Input.Password prefix={<LockOutlined />} autoComplete="new-password" size="large" /></Form.Item><Form.Item name="password_confirmation" label="Xác nhận mật khẩu" dependencies={['password']} rules={[{ required: true, message: 'Vui lòng xác nhận mật khẩu.' }, ({ getFieldValue }) => ({ validator(_, value) { return !value || getFieldValue('password') === value ? Promise.resolve() : Promise.reject(new Error('Mật khẩu xác nhận không khớp.')); } })]}><Input.Password prefix={<LockOutlined />} autoComplete="new-password" size="large" /></Form.Item><Form.Item name="accepted_terms" valuePropName="checked" rules={[{ validator: (_, value) => value ? Promise.resolve() : Promise.reject(new Error('Bạn cần đồng ý điều khoản sử dụng.')) }]}><Checkbox>Tôi đồng ý với điều khoản sử dụng và chính sách bảo mật.</Checkbox></Form.Item><Button type="primary" htmlType="submit" block size="large" loading={submitting}>Đăng ký</Button></Form><p className="register-login">Đã có tài khoản? <a href="/login">Đăng nhập</a></p></>}</Card></main>;
}
