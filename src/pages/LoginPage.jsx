import { useState } from 'react';
import { Alert, Button, Card, Form, Input, Typography } from 'antd';
import { LockOutlined, MailOutlined } from '@ant-design/icons';
import './LoginPage.css';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export default function LoginPage() {
  const [form] = Form.useForm();
  const [submitting, setSubmitting] = useState(false);
  const [apiError, setApiError] = useState('');
  const submit = async (values) => {
    setSubmitting(true); setApiError('');
    try {
      const response = await fetch(`${apiBaseUrl}/auth/login/`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email: values.email, password: values.password }) });
      const data = await response.json();
      if (!response.ok) {
        if (response.status !== 429) form.setFields([{ name: 'email', errors: [' '] }, { name: 'password', errors: [' '] }]);
        setApiError(data.message || 'Không thể đăng nhập.');
        return;
      }
      localStorage.setItem('techzone_user', JSON.stringify(data.user));
      window.location.assign('/');
    } catch { setApiError('Không thể kết nối máy chủ. Vui lòng thử lại sau.'); } finally { setSubmitting(false); }
  };
  return <main className="login-page"><Card className="login-card" bordered={false}><div className="login-heading"><a href="/" className="login-logo">TZ</a><Typography.Title level={2}>Đăng nhập</Typography.Title><Typography.Text>Đăng nhập để theo dõi đơn hàng và nhận ưu đãi từ TechZone.</Typography.Text></div>{apiError && <Alert type="error" showIcon message={apiError} className="login-alert" />}<Form form={form} layout="vertical" onFinish={submit} requiredMark={false}><Form.Item name="email" label="Email" rules={[{ required: true, message: 'Vui lòng nhập email.' }, { type: 'email', message: 'Email không hợp lệ.' }]}><Input prefix={<MailOutlined />} autoComplete="email" placeholder="email@domain.com" size="large" /></Form.Item><Form.Item name="password" label="Mật khẩu" rules={[{ required: true, message: 'Vui lòng nhập mật khẩu.' }]}><Input.Password prefix={<LockOutlined />} autoComplete="current-password" size="large" /></Form.Item><Button type="primary" htmlType="submit" block size="large" loading={submitting}>Đăng nhập</Button></Form><p className="login-register">Chưa có tài khoản? <a href="/register">Đăng ký</a></p></Card></main>;
}
