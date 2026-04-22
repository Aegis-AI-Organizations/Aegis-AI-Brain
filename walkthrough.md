# Walkthrough - Teams Real-Time Updates (SSE)

I have replaced the 10-second polling on the Teams page with a real-time **SSE (Server-Sent Events)** stream. This improves performance and ensures the UI is always in sync with the backend.

## Changes Made

### 1. Proto (`Aegis-AI-Proto`)
- Added `WatchTeams` RPC to `CompanyService`.
- Defined `WatchTeamsRequest` and `WatchTeamsResponse`.
- Regenerated Go and Python gRPC code.

### 2. Brain (`Aegis-AI-Brain`)
- **Broadcaster**: Refactored `StatusBroadcaster` to support generic event types (`scan`, `team`).
- **Service**: Implemented `WatchTeams` streaming method.
- **Events**: Added triggers to broadcast `COMPANY_CREATED` and `USER_CREATED` events after successful database commits.

### 3. API Gateway (`Aegis-AI-Api-Gateway`)
- **Handler**: Created `TeamStreamHandler` to proxy gRPC streams to SSE.
- **Client**: Updated the gRPC client wrapper to support `WatchTeams`.
- **Routes**: Registered `GET /admin/teams/stream`.
- **Tests**: Updated mocks in `company_test.go` and `client_test.go` to maintain test suite stability.

### 4. Dashboard (`Aegis-AI-Dashboard`)
- **Hook**: Created `useTeamsSSE` to manage the SSE connection and trigger callbacks on updates.
- **UI**: Updated `Users.tsx` to use the hook and removed the periodic `setInterval` polling.

## CI/CD Stabilization

I have fixed several regressions in the test suites caused by the transition to SSE:
- **Dashboard**: Fixed `TypeError` in `Users.test.tsx` by adding `defaults.baseURL` to the Axios mock.
- **Brain**: Updated `test_grpc_server.py` to handle the synchronous `broadcast` API and added missing `asyncio` imports.
- **Brain Tests**: Resolved `TypeError` in `test_company_service.py` by using `AsyncMock` for `context.abort` and provided valid identity mocks to pass RBAC decorators.
- **Coverage**: Increased Brain service test coverage to >80% by adding unit tests for `OnboardCompany`, `WatchTeams`, and administrative user creation.

## Verification

### Real-Time Update Flow
1. The Dashboard connects to `/admin/teams/stream`.
2. When an admin creates a company or user, the Brain broadcasts a `team` event.
3. The Gateway receives the gRPC update and sends an SSE message to the Dashboard.
4. The Dashboard receives the message and triggers `fetchCompanies()` to refresh the UI immediately.

All changes have been pushed to the `main` branches of the respective repositories.
