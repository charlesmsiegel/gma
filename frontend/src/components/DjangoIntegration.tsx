import React from 'react';
import { createRoot } from 'react-dom/client';
import { AuthProvider } from '../contexts/AuthContext';
import LoginForm from './LoginForm';
import RegisterForm from './RegisterForm';
import ProfileView from './ProfileView';
import ProfileEditForm from './ProfileEditForm';
import '../styles/index.css';

// Component registry for Django integration
const COMPONENTS = {
  'login-form': LoginForm,
  'register-form': RegisterForm,
  'profile-view': ProfileView,
  'profile-edit-form': ProfileEditForm,
};

// Function to mount React components in Django templates
export const mountComponent = (componentName: string, elementId: string, props: any = {}) => {
  const Component = COMPONENTS[componentName as keyof typeof COMPONENTS];
  const element = document.getElementById(elementId);

  if (!Component) {
    console.error(`Component "${componentName}" not found`);
    return;
  }

  if (!element) {
    console.error(`Element with id "${elementId}" not found`);
    return;
  }

  const root = createRoot(element);
  root.render(
    <AuthProvider>
      <Component {...props} />
    </AuthProvider>
  );
};

// Enhanced versions with success callbacks for Django integration
export const LoginFormWithRedirect: React.FC<{ redirectUrl?: string }> = ({ redirectUrl }) => (
  <LoginForm
    onSuccess={() => {
      if (redirectUrl) {
        window.location.href = redirectUrl;
      } else {
        window.location.reload();
      }
    }}
  />
);

export const RegisterFormWithRedirect: React.FC<{ redirectUrl?: string }> = ({ redirectUrl }) => (
  <RegisterForm
    onSuccess={() => {
      if (redirectUrl) {
        window.location.href = redirectUrl;
      } else {
        window.location.reload();
      }
    }}
  />
);

export const ProfileEditFormWithRedirect: React.FC<{ redirectUrl?: string }> = ({ redirectUrl }) => (
  <ProfileEditForm
    onSuccess={() => {
      if (redirectUrl) {
        window.location.href = redirectUrl;
      } else {
        window.location.reload();
      }
    }}
    onCancel={() => {
      window.history.back();
    }}
  />
);

// Add enhanced components to registry
const ENHANCED_COMPONENTS = {
  ...COMPONENTS,
  'login-form-redirect': LoginFormWithRedirect,
  'register-form-redirect': RegisterFormWithRedirect,
  'profile-edit-form-redirect': ProfileEditFormWithRedirect,
};

export const mountEnhancedComponent = (componentName: string, elementId: string, props: any = {}) => {
  const Component = ENHANCED_COMPONENTS[componentName as keyof typeof ENHANCED_COMPONENTS];
  const element = document.getElementById(elementId);

  if (!Component) {
    console.error(`Component "${componentName}" not found`);
    return;
  }

  if (!element) {
    console.error(`Element with id "${elementId}" not found`);
    return;
  }

  const root = createRoot(element);
  root.render(
    <AuthProvider>
      <Component {...props} />
    </AuthProvider>
  );
};
