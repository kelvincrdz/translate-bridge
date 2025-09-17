import React from 'react';
import { Toaster } from './components/ui/sonner';
import { AppProvider, useApp } from './context/AppContext';
import { LoginScreen } from './components/LoginScreen';
import { Library } from './components/Library';
import { EpubReader } from './components/EpubReader';

function AppContent() {
  const { state } = useApp();

  const renderCurrentView = () => {
    switch (state.currentView) {
      case 'login':
        return <LoginScreen />;
      case 'library':
        return <Library />;
      case 'reader':
        return <EpubReader />;
      default:
        return <LoginScreen />;
    }
  };

  return (
    <div className={`min-h-screen ${state.globalTheme === 'dark' ? 'dark' : ''}`}>
      {renderCurrentView()}
      <Toaster position="top-right" />
    </div>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}