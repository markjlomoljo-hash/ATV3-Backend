# AcneTrex v3 Upgrade: Phase 3 Implementation Plan

**Date**: June 23, 2026  
**Status**: Planning  
**Phase**: 3 - Broken-Flow Repair and Refinement

## Overview

Phase 3 focuses on identifying and repairing broken flows, integrating Phase 1 and Phase 2 components, and ensuring seamless user experience across all features. This phase emphasizes end-to-end testing and production readiness.

## Broken-Flow Categories and Repairs

### 1. Same-Day Log Merge

**Current State**: Backend correctly implements same-day log merge in `log_service.py`

**Required Frontend Integration**:

- **Form Submission**: When user submits a log for today, check if a log of the same type already exists
- **UI Feedback**: Show "Updating today's log" instead of "Creating new log"
- **Idempotency**: Use `useDoubleSubmitGuard` hook to prevent double-submission
- **Conflict Resolution**: If concurrent submissions occur, show user the merged result

**Implementation Files to Create**:

- `frontend/src/features/logs/hooks/useLogMerge.ts` - Hook for log merge logic
- `frontend/src/features/logs/components/LogForm.tsx` - Form with merge awareness

**Code Pattern**:

```typescript
const useLogMerge = (logType: string, logDate: Date) => {
  const [existingLog, setExistingLog] = useState(null);
  
  useEffect(() => {
    // Check if a log of this type exists for this date
    const checkExistingLog = async () => {
      const logs = await logsApi.getByDateAndType(logDate, logType);
      setExistingLog(logs[0] || null);
    };
    checkExistingLog();
  }, [logType, logDate]);
  
  return { existingLog, isUpdate: !!existingLog };
};
```

### 2. Onboarding Gates and Flow

**Current State**: `OnboardingProfile` model exists, onboarding routes exist

**Required Repairs**:

- **Route Protection**: Protect all app routes except onboarding until `onboarding.completed === true`
- **Step Progression**: Ensure users cannot skip onboarding steps
- **Data Validation**: Validate each onboarding step before allowing progression
- **Recovery**: Allow users to return to incomplete onboarding

**Implementation Files to Create**:

- `frontend/src/features/onboarding/hooks/useOnboardingFlow.ts` - Onboarding state management
- `frontend/src/features/onboarding/components/OnboardingGate.tsx` - Route protection component
- `frontend/src/features/onboarding/pages/OnboardingStep*.tsx` - Individual step pages

**Code Pattern**:

```typescript
const OnboardingGate: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { onboarding, loading } = useOnboarding(user?.id);
  
  if (loading) return <LoadingSpinner />;
  if (!onboarding?.completed) return <Navigate to="/onboarding" />;
  
  return <>{children}</>;
};
```

### 3. Route Redirects and Navigation

**Current State**: Routes defined in backend, frontend navigation needs implementation

**Required Repairs**:

- **Auth Redirects**: Redirect unauthenticated users to login
- **Onboarding Redirects**: Redirect users with incomplete onboarding to onboarding flow
- **404 Handling**: Handle non-existent routes gracefully
- **Deep Linking**: Support direct navigation to app features after auth

**Implementation Files to Create**:

- `frontend/src/router/index.ts` - React Router configuration
- `frontend/src/router/ProtectedRoute.tsx` - Auth-protected route wrapper
- `frontend/src/router/OnboardingRoute.tsx` - Onboarding-protected route wrapper

**Code Pattern**:

```typescript
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { path: "login", element: <LoginPage /> },
      { path: "signup", element: <SignupPage /> },
      {
        element: <ProtectedRoute />,
        children: [
          {
            element: <OnboardingGate />,
            children: [
              { path: "dashboard", element: <DashboardPage /> },
              { path: "scans", element: <ScansPage /> },
              // ... more routes
            ],
          },
        ],
      },
    ],
  },
]);
```

### 4. Race-Condition Guards

**Current State**: `useDoubleSubmitGuard` hook created in Phase 1

**Required Integration**:

- **Log Forms**: Apply guard to all daily log submission handlers
- **Scan Triggers**: Apply guard to scan capture and upload buttons
- **AI Triggers**: Apply guard to forecast generation, product analysis, assistant messages
- **Report Export**: Apply guard to export buttons

**Implementation Pattern**:

```typescript
const LogForm: React.FC = () => {
  const { isSubmitting, withGuard } = useDoubleSubmitGuard();
  
  const handleSubmit = withGuard(async (data) => {
    const result = await logsApi.createOrUpdateLog(data);
    return result;
  });
  
  return (
    <form onSubmit={handleSubmit}>
      {/* form fields */}
      <button disabled={isSubmitting} type="submit">
        {isSubmitting ? "Saving..." : "Save Log"}
      </button>
    </form>
  );
};
```

### 5. Empty and Insufficient Data States

**Current State**: `EmptyState` and `InsufficientDataState` components created in Phase 1

**Required Integration**:

- **Dashboard**: Show empty state when no data exists
- **Scans**: Show insufficient data state if fewer than 10 scans
- **Forecast**: Show insufficient data state if fewer than 7 days of history
- **Trigger Graph**: Show insufficient data state if fewer than 14 days of history
- **Skin Twin**: Show insufficient data state if fewer than 10 scans
- **CHI**: Show insufficient data state if fewer than 3 logs

**Implementation Pattern**:

```typescript
const ForecastPage: React.FC = () => {
  const { scans, loading } = useScans();
  const { logs, loading: logsLoading } = useLogs();
  
  if (loading || logsLoading) return <LoadingSpinner />;
  
  const totalHistory = scans.length + logs.length;
  
  if (totalHistory === 0) {
    return (
      <EmptyState
        icon={BarChart3}
        title="No Data Yet"
        description="Start by logging your daily activities and taking face scans"
        ctaLabel="Get Started"
        ctaRoute="/logs"
      />
    );
  }
  
  if (totalHistory < DATA_THRESHOLDS.FORECAST_MIN_DAYS) {
    return (
      <InsufficientDataState
        moduleName="Forecast"
        requiredDataPoints={DATA_THRESHOLDS.FORECAST_MIN_DAYS}
        currentDataPoints={totalHistory}
        ctaLabel="Add More Data"
        ctaRoute="/logs"
      />
    );
  }
  
  return <ForecastContent />;
};
```

### 6. Auth Layer Hardening

**Current State**: Basic auth implemented in backend

**Required Enhancements**:

- **Session Persistence**: Implement "Remember Me" functionality
- **Token Refresh**: Implement JWT refresh token rotation
- **Logout Revocation**: Ensure logout immediately revokes sessions
- **Password Reset**: Implement secure password reset flow
- **Email Verification**: Implement email verification for new accounts

**Implementation Files to Create**:

- `frontend/src/features/auth/hooks/useAuth.ts` - Auth state management
- `frontend/src/features/auth/services/authService.ts` - Auth API calls
- `frontend/src/features/auth/pages/LoginPage.tsx` - Login form
- `frontend/src/features/auth/pages/SignupPage.tsx` - Signup form
- `frontend/src/features/auth/pages/ResetPasswordPage.tsx` - Password reset

### 7. Data Continuity and Migration

**Current State**: Migration endpoint exists at `POST /v1/auth/migrate`

**Required Frontend Integration**:

- **Migration Trigger**: Show migration prompt after login if legacy data exists
- **Migration Progress**: Display progress during migration
- **Migration Confirmation**: Show summary of imported data
- **Migration Errors**: Handle and display migration errors gracefully

**Implementation Files to Create**:

- `frontend/src/features/auth/components/MigrationDialog.tsx` - Migration UI
- `frontend/src/features/auth/hooks/useMigration.ts` - Migration logic

**Code Pattern**:

```typescript
const useMigration = () => {
  const [migrating, setMigrating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const runMigration = async (legacyData: LegacyData) => {
    setMigrating(true);
    try {
      const result = await authApi.migrate({
        legacy_auth_v2: legacyData.auth,
        legacy_data_v2: legacyData.data,
        legacy_ai_v2: legacyData.ai,
        consent_to_import: true,
      });
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setMigrating(false);
    }
  };
  
  return { runMigration, migrating, error };
};
```

## Feature Integration Checklist

### Dashboard
- [ ] Display empty state if no data exists
- [ ] Show intelligence status (AI/ML readiness)
- [ ] Show quick stats from latest data
- [ ] Show motivational task board

### Logs
- [ ] Implement same-day merge UI
- [ ] Apply double-submit guard
- [ ] Show confirmation after save
- [ ] Display log history

### Scans
- [ ] Implement camera capture flow
- [ ] Show scan quality feedback
- [ ] Apply double-submit guard
- [ ] Display scan history with results

### Forecast
- [ ] Show insufficient data state if needed
- [ ] Display current risk and forecasted risk
- [ ] Show key drivers and recommendations
- [ ] Implement what-if simulator

### Assistant
- [ ] Implement conversation UI
- [ ] Show evidence citations
- [ ] Display confidence score
- [ ] Apply double-submit guard

### Products
- [ ] Implement product upload/entry
- [ ] Show ingredient analysis
- [ ] Display risk assessment
- [ ] Apply double-submit guard

## Testing Strategy

### Unit Tests
- Test each hook and component in isolation
- Test validation logic
- Test error handling

### Integration Tests
- Test complete user flows (login → onboarding → logging → forecast)
- Test same-day merge behavior
- Test race condition prevention
- Test empty/insufficient data states

### End-to-End Tests
- Test complete user journey from signup to advanced features
- Test data persistence across sessions
- Test migration from legacy data
- Test all intelligence engines

### Performance Tests
- Test page load times
- Test API response times
- Test large data set handling

## Deployment Checklist

- [ ] All Phase 1 components integrated
- [ ] All Phase 2 engines integrated
- [ ] All broken flows repaired
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Security audit completed
- [ ] Accessibility audit completed
- [ ] Documentation updated
- [ ] User guide created
- [ ] Deployment plan finalized

## Success Criteria

1. **Zero Broken Flows**: All user journeys complete without errors
2. **Data Integrity**: All data persisted correctly with audit trails
3. **Performance**: Page load < 2s, API response < 500ms
4. **Accessibility**: WCAG 2.1 Level AA compliance
5. **Security**: All security best practices implemented
6. **User Experience**: Intuitive, responsive, mobile-friendly
7. **Reliability**: 99.9% uptime, zero data loss
8. **Compliance**: Zero-Fabrication Contract fully satisfied

## Timeline

- **Week 1**: Same-day merge, onboarding gates, route redirects
- **Week 2**: Race-condition guards, empty states, auth hardening
- **Week 3**: Data migration, integration testing
- **Week 4**: Performance optimization, security audit, deployment prep

## Files to Create

### Frontend Features
- `src/features/logs/` - Logging feature
- `src/features/scans/` - Scan capture feature
- `src/features/forecast/` - Forecast feature
- `src/features/assistant/` - Assistant feature
- `src/features/products/` - Product analysis feature
- `src/features/onboarding/` - Onboarding feature
- `src/features/auth/` - Authentication feature
- `src/router/` - Router configuration

### Hooks and Services
- `src/lib/hooks/` - Custom React hooks
- `src/lib/services/` - API services

### Pages
- `src/pages/` - Top-level page components

## Next Steps

After Phase 3 completion:
1. Deploy to staging environment
2. Conduct user acceptance testing
3. Gather feedback and iterate
4. Deploy to production
5. Monitor and optimize
6. Plan Phase 4 enhancements (advanced features, mobile app, etc.)

## References

- Architecture Plan: `architecture_plan.md`
- Phase 1 Implementation: `PHASE1_IMPLEMENTATION.md`
- Phase 2 Implementation: `PHASE2_IMPLEMENTATION.md`
- Upgrade Skill: `/home/ubuntu/skills/acnetrex-v3-upgrade/SKILL.md`
