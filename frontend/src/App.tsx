import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RootLayout } from './layouts/RootLayout';

import { HomePage } from './pages/HomePage';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { ExplorerPage } from './pages/ExplorerPage';
import { IssuesPage } from './pages/IssuesPage';
import { GraphPage } from './pages/GraphPage';
import { RiskPage } from './pages/RiskPage';
import { PrReviewPage } from './pages/PrReviewPage';
import { EvaluationPage } from './pages/EvaluationPage';
import { GitHubValidatePage } from './pages/GitHubValidatePage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <RootLayout>
          <Routes>
            <Route path="/" element={<GitHubValidatePage />} />
            <Route path="/home-old" element={<HomePage />} />
            <Route path="/dashboard" element={<Navigate to="/repositories/repo-fastapi-backend" replace />} />
            <Route path="/repositories/:id" element={<DashboardPage />} />
            <Route path="/repositories/:id/chat" element={<ChatPage />} />
            <Route path="/repositories/:id/explorer" element={<ExplorerPage />} />
            <Route path="/repositories/:id/issues" element={<IssuesPage />} />
            <Route path="/repositories/:id/graph" element={<GraphPage />} />
            <Route path="/repositories/:id/risk" element={<RiskPage />} />
            <Route path="/repositories/:id/pr-review" element={<PrReviewPage />} />
            <Route path="/evaluation" element={<EvaluationPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </RootLayout>
      </Router>
    </QueryClientProvider>
  );
};

export default App;
