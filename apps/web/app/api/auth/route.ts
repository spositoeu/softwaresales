import { sign } from 'nextjs/headers';
import { PrismaClient } from '@prisma/client';
import { updateUser } from '@/lib/db';

const prisma = new PrismaClient();

export async function login(request) {
  const { email, password } = await request.json();

  try {
    const user = await prisma.user.findUnique({
      where: { email },
    });

    if (!user) {
      return { error: 'Invalid credentials' };
    }

    if (!user.passwordMatches(password)) {
      return { error: 'Invalid credentials' };
    }

    const token = sign({
      id: user.id,
      email: user.email,
      role: user.role,
    });

    await updateUser({ id: user.id, hashedPassword: user.password });

    return { token };
  } catch (error) {
    console.error('Login error:', error);
    return { error: 'Failed to login' };
  }
}

export default login;
```
```
MODIFICA: apps/web/app/api/products/route.ts
COMMIT_MSG: Implement GET /products endpoint
CONTENUTO:
```typescript
import { NextResponse } from 'next/server';
import prisma from '@/lib/db';

export async function GET(request) {
  try {
    const products = await prisma.product.findMany();
    return NextResponse.json(products);
  } catch (error) {
    console.error('Error fetching products:', error);
    return NextResponse.json({ error: 'Failed to fetch products' }, { status: 500 });
  }
}
```
```
MODIFICA: turbo.json
COMMIT_MSG: Add new package.json scripts
CONTENUTO:
```json
{
  "version": 2,
  "packages": [
    {
      "name": "my-project",
      "version": "1.0.0",
      "dependencies": {
        "@prisma/client": "^4.10.1",
        "cuid2": "^2.0.1",
        "next": "^13.4.12",
        "react": "^18.2.0",
        "react-dom": "^18.2.0",
        "stripe": "^12.3.0",
        "zod": "^3.21.0"
      }
    }
  ],
  "scripts": {
    "dev": "turbo run dev --parallel",
    "build": "turbo run build --stop-on-error",
    "lint": "turbo run lint",
    "clean": "turbo run clean",
    "start": "turbo run start"
  }
}
```
```
MODIFICA: .gitignore
COMMIT_MSG: Add more files to ignore
CONTENUTO:
```
# Ignora
node_modules
.next
.next-dev
out
.env
.env.local
.typicode/responses
```
```
MODIFICA: package.json
COMMIT_MSG: Add initial dependencies
CONTENUTO:
```json
{
  "name": "my-project",
  "version": "1.0.0",
  "description": "E-commerce App",
  "main": "index.js",
  "scripts": {
    "dev": "turbo run dev --parallel",
    "build": "turbo run build --stop-on-error",
    "lint": "turbo run lint",
    "clean": "turbo run clean",
    "start": "turbo run start"
  },
  "keywords": [],
  "author": "",
  "license": "ISC",
  "dependencies": {
    "@prisma/client": "^4.10.1",
    "cuid2": "^2.0.1",
    "next": "^13.4.12",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "stripe": "^12.3.0",
    "zod": "^3.21.0"
  },
  "devDependencies": {
    "@types/node": "^18.11.19",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "eslint": "^8.49.0",
    "eslint-config-next": "^13.4.12",
    "husky": "^8.0.3",
    "turbo": "^1.0.15"
  }
}
```
```
MODIFICA: apps/web/components/ui/button.tsx
COMMIT_MSG: Implement button component
CONTENUTO:
```typescript
import React from 'react';
import styles from './button.module.css';

interface ButtonProps {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
  onClick?: () => void;
}

const Button: React.FC<ButtonProps> = ({ children, variant = 'primary', disabled = false, onClick }) => {
  const className = `${styles.button} ${styles[variant]}`;

  return (
    <button className={className} disabled={disabled} onClick={onClick}>
      {children}
    </button>
  );
};

export default Button;
```
```
MODIFICA: apps/web/styles/globals.css
COMMIT_MSG: Add base styles
CONTENUTO:
```css
body {
  margin: 0;
  font-family: -apple-sink, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  transition: color 150ms ease-in-out;
}

/* Prevents scrollbars from appearing on mobile */
body,
html {
  height: 100%;
}
```
```
MODIFICA: apps/web/app/layout.tsx
COMMIT_MSG: Add global styles and header
CONTENUTO:
```typescript
import type { Roboto } from 'next/font';
import './styles/globals.css';
import Header from './components/ui/header';

const roboto = Roboto({
  weight: '400',
  subsets: ['en'],
});

export default function RootLayout(props: React.Props<typeof RootLayout>) {
  return (
    <html lang="en">
      <body className={roboto.className}>
        <Header />
        {props.children}
      </body>
    </html>
  );
}
```
```
MODIFICA: apps/web/components/ui/header.tsx
COMMIT_MSG: Implement basic header
CONTENUTO:
```typescript
import React from 'react';
import Link from 'next/link';
import Button from './button';
import styles from './header.module.css';

const Header = () => {
  return (
    <header className={styles.header}>
      <div className={styles.container}>
        <div className={styles.left}>
          <Link href="/" className={styles.logo}>
            My E-commerce App
          </Link>
        </div>
        <div className={styles.right}>
          <Button variant="secondary">Login</Button>
        </div>
      </div>
    </header>
  );
};

export default Header;