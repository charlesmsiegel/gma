import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginForm from './components/LoginForm';
import RegisterForm from './components/RegisterForm';
import ProfileView from './components/ProfileView';
import ProfileEditForm from './components/ProfileEditForm';
import './styles/index.css';

type View = 'login' | 'register' | 'profile' | 'profile-edit';

const AuthenticatedApp: React.FC = () => {
  const { user, logout } = useAuth();
  const [view, setView] = useState<View>('profile');

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <div className="container">
      <header style={{ padding: '1rem 0', borderBottom: '1px solid #ddd', marginBottom: '2rem' }}>
        <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h1>Game Master Application</h1>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <span>Welcome, {user?.display_name || user?.username}!</span>
            <button
              className="btn btn-secondary"
              onClick={() => setView('profile')}
            >
              Profile
            </button>
            <button
              className="btn btn-secondary"
              onClick={handleLogout}
            >
              Logout
            </button>
          </div>
        </nav>
      </header>

      <main>
        {view === 'profile' && (
          <ProfileView onEdit={() => setView('profile-edit')} />
        )}
        {view === 'profile-edit' && (
          <ProfileEditForm
            onSuccess={() => setView('profile')}
            onCancel={() => setView('profile')}
          />
        )}
      </main>
    </div>
  );
};

const UnauthenticatedApp: React.FC = () => {
  const [view, setView] = useState<View>('login');

  return (
    <div className="container">
      <header style={{ padding: '1rem 0', marginBottom: '2rem' }}>
        <h1 className="text-center">Game Master Application</h1>
      </header>

      <main>
        {view === 'login' && (
          <LoginForm
            onSuccess={() => window.location.reload()}
            onSwitchToRegister={() => setView('register')}
          />
        )}
        {view === 'register' && (
          <RegisterForm
            onSuccess={() => window.location.reload()}
            onSwitchToLogin={() => setView('login')}
          />
        )}
      </main>
    </div>
  );
};

const AppContent: React.FC = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="container">
        <div className="text-center" style={{ padding: '4rem 0' }}>
          <div>Loading...</div>
        </div>
      </div>
    );
  }

  return user ? <AuthenticatedApp /> : <UnauthenticatedApp />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
