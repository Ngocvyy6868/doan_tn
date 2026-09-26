import React, { useEffect, useMemo, useState } from 'react';
import {
  Search, ShoppingCart, User, ChevronRight, Menu, Microchip, Cpu, MemoryStick,
  HardDrive, Box, Zap, MapPin, Gamepad, Monitor, Laptop, Wrench, Newspaper,
  Plus, Minus, X, ShieldCheck, ArrowRight,
} from 'lucide-react';
import Builder from './PcBuilder.jsx';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const cats = [
  ['CPU', Cpu],
  ['VGA', Microchip],
  ['Mainboard', MemoryStick],
  ['RAM', MemoryStick],
  ['SSD', HardDrive],
  ['Nguồn', Zap],
  ['Case', Box],
];

export const navLinks = [
  { name: 'PC BUILDER', icon: Microchip, ai: true, href: '#' },
  { name: 'PC GAMING', icon: Gamepad, href: '/pc-gaming' },
  { name: 'LAPTOP', icon: Laptop, href: '/laptop' },
  { name: 'MÀN HÌNH', icon: Monitor, href: '/monitor' },
  { name: 'PHỤ KIỆN', icon: Wrench, href: '/accessories' },
  { name: 'TIN CÔNG NGHỆ', icon: Newspaper, href: '/tech-news' },
];

export const money = (n) => n.toLocaleString('vi-VN') + '₫';
export const categorySlug = (name) =>
  encodeURIComponent(
    name
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/đ/g, 'd')
      .replace(/\s+/g, '-'),
  );

export const readStore = (key, fallback) => {
  try {
    return JSON.parse(localStorage.getItem(key)) || fallback;
  } catch {
    return fallback;
  }
};

export const writeStore = (key, value) => localStorage.setItem(key, JSON.stringify(value));

export const addToStoredCart = (product) => {
  const cart = readStore('techzone_cart', []);
  const found = cart.find((x) => x.id === product.id);
  const limit = Number.isFinite(product.stock) ? product.stock : 99;
  const next = found
    ? cart.map((x) => (x.id === product.id ? { ...x, q: Math.min(x.q + 1, limit) } : x))
    : [...cart, { ...product, q: 1 }];
  writeStore('techzone_cart', next);
  window.dispatchEvent(new CustomEvent('techzone:cart'));
  return next;
};

export const doLogout = () =>
  fetch(`${apiBaseUrl}/auth/logout/`, { method: 'POST', credentials: 'include' })
    .catch(() => {})
    .finally(() => {
      localStorage.removeItem('techzone_user');
      location.href = '/';
    });

function SiteFooter() {
  return (
    <footer>
      <a className="logo" href="/">
        <span>TZ</span>
        <b>
          TECHZONE<small>BUILD YOUR POWER</small>
        </b>
      </a>
      <p>Hệ sinh thái linh kiện và giải pháp PC toàn diện.</p>
      <div>© 2026 TechZone. All rights reserved.</div>
    </footer>
  );
}

export default function SiteLayout({ children, products = [], showFooter = true }) {
  const catalog = useMemo(() => {
    try {
      return JSON.parse(localStorage.getItem('techzone_products')) || products;
    } catch {
      return products;
    }
  }, [products]);

  const [account] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('techzone_user'));
    } catch {
      return null;
    }
  });
  const [accountMenu, setAccountMenu] = useState(false);
  const [query, setQuery] = useState('');
  const [cart, setCart] = useState(() => readStore('techzone_cart', []));
  const [drawer, setDrawer] = useState(false);
  const [builder, setBuilder] = useState(false);
  const [mobileMenu, setMobileMenu] = useState(false);
  const [catOpen, setCatOpen] = useState(false);

  useEffect(() => writeStore('techzone_cart', cart), [cart]);

  useEffect(() => {
    const sync = () => setCart(readStore('techzone_cart', []));
    window.addEventListener('techzone:cart', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('techzone:cart', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  useEffect(() => {
    const close = (e) => {
      if (!e.target.closest?.('.nav-catalog-wrap')) setCatOpen(false);
      if (!e.target.closest?.('.account-menu-wrap')) setAccountMenu(false);
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, []);

  const searchResults = useMemo(
    () =>
      catalog
        .filter(
          (p) =>
            p.active !== false &&
            (p.name.toLowerCase().includes(query.toLowerCase()) ||
              p.brand?.toLowerCase().includes(query.toLowerCase())),
        )
        .slice(0, 6),
    [query, catalog],
  );

  const add = (p) => {
    setCart((c) => {
      const f = c.find((x) => x.id === p.id);
      const limit = Number.isFinite(p.stock) ? p.stock : 99;
      return f
        ? c.map((x) => (x.id === p.id ? { ...x, q: Math.min(x.q + 1, limit) } : x))
        : [...c, { ...p, q: 1 }];
    });
    setDrawer(true);
  };

  const count = cart.reduce((s, x) => s + x.q, 0);
  const total = cart.reduce((s, x) => s + x.price * x.q, 0);
  const quantity = (id, d) =>
    setCart((c) => c.map((x) => (x.id === id ? { ...x, q: x.q + d } : x)).filter((x) => x.q > 0));

  const openBuilder = () => {
    setBuilder(true);
    setMobileMenu(false);
    setCatOpen(false);
  };

  const catalogMenu = (
    <div className="nav-catalog-dropdown">
      {cats.map(([name, Icon]) => (
        <a key={name} href={`/collections/${categorySlug(name)}`} onClick={() => setCatOpen(false)}>
          <Icon />
          <span>{name}</span>
          <ChevronRight />
        </a>
      ))}
      <a href="/collections/all" onClick={() => setCatOpen(false)}>
        <Box />
        <span>Xem tất cả sản phẩm</span>
        <ChevronRight />
      </a>
    </div>
  );

  const renderNavLinks = (iconSize, closeMobile) =>
    navLinks.map((x) => (
      <a
        key={x.name}
        href={x.href}
        onClick={(e) => {
          if (x.name === 'PC BUILDER') {
            e.preventDefault();
            openBuilder();
          }
          if (closeMobile) setMobileMenu(false);
        }}
      >
        <x.icon size={iconSize} />
        {x.name}
        {x.ai && <span className="nav-ai-badge">AI</span>}
      </a>
    ));

  return (
    <>
      <div className="topbar">
        <span>TechZone • Giá tốt mỗi ngày</span>
        <div>
          Hotline: <b>1900 6868</b>
          <i /> Tra cứu đơn hàng <i /> Hệ thống cửa hàng
        </div>
      </div>

      <header>
        <a className="logo" href="/">
          <span>TZ</span>
          <b>
            TECHZONE<small>BUILD YOUR POWER</small>
          </b>
        </a>
        <div className="search-container">
          <div className="search">
            <Search size={20} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Bạn cần tìm linh kiện gì?"
            />
            <button type="button" onClick={() => query && (location.href = `/collections/all`)}>
              Tìm kiếm
            </button>
          </div>
          {query.length > 0 && (
            <div className="search-dropdown">
              {searchResults.length > 0 ? (
                searchResults.map((p, index) => (
                  <a
                    key={`${p.id}-${index}`}
                    href={`/product/${p.id}`}
                    className="search-result-item"
                  >
                    <img src={p.img} alt={p.name} />
                    <div>
                      <b>{p.name}</b>
                      <small>
                        {p.brand} • {p.cat}
                      </small>
                    </div>
                    <strong>{money(p.price)}</strong>
                  </a>
                ))
              ) : (
                <div className="search-empty">Không tìm thấy sản phẩm phù hợp</div>
              )}
            </div>
          )}
        </div>
        <div className="actions">
          <div className="account-menu-wrap">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                account ? setAccountMenu((v) => !v) : (location.href = '/login');
              }}
            >
              <User />
              <span>
                {account?.full_name || 'Tài khoản'}
                <small>{account ? 'Đã đăng nhập' : 'Đăng nhập'}</small>
              </span>
            </button>
            {account && accountMenu && (
              <div className="account-dropdown">
                <a href="/profile">
                  <User />
                  Thông tin cơ bản
                </a>
                <a href="/addresses">
                  <MapPin />
                  Sổ địa chỉ
                </a>
                <a href="/orders">
                  <ShoppingCart />
                  Đơn hàng của tôi
                </a>
                <button type="button" className="logout" onClick={doLogout}>
                  Thoát
                </button>
              </div>
            )}
          </div>
          <button type="button" onClick={() => setDrawer(true)}>
            <ShoppingCart />
            <span>
              Giỏ hàng<small>{count} sản phẩm</small>
            </span>
            {count > 0 && <em>{count}</em>}
          </button>
          <button type="button" className="hamb" onClick={() => setMobileMenu((v) => !v)}>
            <Menu />
          </button>
        </div>
      </header>

      <nav>
        <div className="nav-catalog-wrap">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setCatOpen((v) => !v);
            }}
          >
            <Menu size={18} /> DANH MỤC SẢN PHẨM
          </button>
          {catOpen && catalogMenu}
        </div>
        {renderNavLinks(16)}
      </nav>

      {mobileMenu && <div className="mobile-nav-overlay" onClick={() => setMobileMenu(false)} />}
      {mobileMenu && (
        <div className="mobile-nav-menu">
          <div className="mobile-nav-cats">
            <b>Danh mục</b>
            {cats.map(([name, Icon]) => (
              <a
                key={name}
                href={`/collections/${categorySlug(name)}`}
                onClick={() => setMobileMenu(false)}
              >
                <Icon size={20} />
                {name}
              </a>
            ))}
          </div>
          {renderNavLinks(20, true)}
        </div>
      )}

      {typeof children === 'function' ? children({ add, catalog, openBuilder, cart }) : children}

      {showFooter && <SiteFooter />}

      {drawer && (
        <>
          <div className="shade" onClick={() => setDrawer(false)} />
          <aside className="drawer">
            <div className="drawer-head">
              <h2>
                Giỏ hàng <span>({count})</span>
              </h2>
              <button type="button" onClick={() => setDrawer(false)}>
                <X />
              </button>
            </div>
            <div className="cart-list">
              {cart.length ? (
                cart.map((x) => (
                  <div className="cart-item" key={x.id}>
                    <img src={x.img} alt={x.name} />
                    <div>
                      <b>{x.name}</b>
                      <strong>{money(x.price)}</strong>
                      <div className="qty">
                        <button type="button" onClick={() => quantity(x.id, -1)}>
                          <Minus />
                        </button>
                        <span>{x.q}</span>
                        <button type="button" onClick={() => quantity(x.id, 1)}>
                          <Plus />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="cart-empty">
                  <ShoppingCart />
                  <h3>Giỏ hàng đang trống</h3>
                  <p>Khám phá linh kiện phù hợp cho bộ PC của bạn.</p>
                </div>
              )}
            </div>
            {cart.length > 0 && (
              <div className="checkout">
                <div>
                  <span>Tạm tính</span>
                  <b>{money(total)}</b>
                </div>
                <button type="button" onClick={() => (location.href = '/checkout')}>
                  TIẾN HÀNH THANH TOÁN <ArrowRight />
                </button>
                <small>
                  <ShieldCheck /> Thanh toán an toàn & bảo mật
                </small>
              </div>
            )}
          </aside>
        </>
      )}

      {builder && <Builder close={() => setBuilder(false)} add={add} products={catalog} />}
    </>
  );
}
