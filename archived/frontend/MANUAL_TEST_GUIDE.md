# Manual Testing Guide for Authentication GUI

This guide provides instructions for manually testing the authentication GUI components.

## Prerequisites

1. **Frontend setup**:
   ```bash
   cd frontend
   uv sync
   ```

2. **Backend running (optional but recommended)**:
   ```bash
   cd ../backend
   uv run python manage.py runserver 8001
   ```

## Running the Manual Test App

1. **Start the test application**:
   ```bash
   cd frontend
   uv run python manual_auth_test.py
   ```

2. **Expected result**: A GUI window should open with authentication controls

## Test Scenarios

### 1. User Registration Test

**Steps**:
1. Click the "Register" button
2. A registration dialog should appear
3. Fill in the form:
   - Username: `testuser`
   - Email: `test@example.com`
   - Display Name: `Test User` (optional)
   - Password: `password123`
   - Confirm Password: `password123`
4. Click "Create Account"

**Expected Results**:
- Registration dialog should show loading state
- If backend is running: Should create account and auto-login
- If backend is not running: Should show network error
- Dialog should close on success
- Main window should show "Logged in as Test User (testuser)"
- Login/Register buttons should become disabled
- Logout button should become enabled

### 2. User Login Test

**Steps**:
1. If logged in, click "Logout" first
2. Click the "Login" button
3. A login dialog should appear
4. Fill in the form:
   - Username: `admin` (or your registered username)
   - Password: `admin123` (or your password)
5. Optionally check "Remember me"
6. Click "Login"

**Expected Results**:
- Login dialog should show loading state
- If credentials are correct: Should login successfully
- If credentials are wrong: Should show error message
- If backend is not running: Should show network error
- Dialog should close on success
- UI should update to show logged-in state

### 3. Form Validation Tests

**Registration Form Validation**:
1. Click "Register"
2. Try submitting with empty fields → Should show validation errors
3. Try password mismatch → Should show "Passwords do not match"
4. Try invalid email format → Should show "Invalid email address"
5. Try short password → Should show "Password must be at least 8 characters"

**Login Form Validation**:
1. Click "Login"
2. Try submitting with empty username → Should show "Username is required"
3. Try submitting with empty password → Should show "Password is required"
4. Try very short password → Should show "Password must be at least 4 characters"

### 4. Password Visibility Toggle

**Steps**:
1. Click "Login"
2. Type a password in the password field
3. Click the eye icon (👁) next to the password field
4. Password should become visible
5. Click the eye icon again
6. Password should become hidden again

### 5. Profile Management Test

**Steps**:
1. Login with one account
2. Logout
3. Register or login with a different account
4. Click "Refresh Profiles" button
5. Use the "Profiles" dropdown to switch between accounts

**Expected Results**:
- Dropdown should show saved profile names
- Selecting a profile should switch to that user (if token is still valid)
- UI should update to show the selected user's information

### 6. Loading States Test

**Steps**:
1. Click "Login" or "Register"
2. Observe the form during authentication
3. Try clicking buttons multiple times during loading

**Expected Results**:
- Loading indicator should appear ("Logging in..." or "Creating account...")
- Form fields should be disabled during loading
- Buttons should be disabled during loading
- No double-submission should occur

### 7. Error Handling Test

**Steps**:
1. Make sure backend is NOT running
2. Try to login or register
3. Try with invalid credentials (if backend is running)

**Expected Results**:
- Network errors should show appropriate messages
- Invalid credentials should show "Invalid username or password"
- Registration with existing username should show appropriate error
- Error messages should be user-friendly

### 8. Dialog Navigation Test

**Steps**:
1. Click "Login"
2. In login dialog, click "Register"
3. Should switch to registration dialog
4. In registration dialog, click "Back to Login"
5. Should switch back to login dialog
6. Click "Cancel" in either dialog

**Expected Results**:
- Dialogs should switch smoothly
- Previous form data should be cleared when switching
- Cancel should close dialog without action

### 9. Configuration Test

**Steps**:
1. Create a `.env` file in frontend directory:
   ```
   GOMOKU_BASE_URL=http://localhost:8001
   GOMOKU_LOG_LEVEL=DEBUG
   GOMOKU_AUTO_REFRESH_TOKEN=true
   ```
2. Restart the test app
3. Check console output for configuration loading

**Expected Results**:
- Should see debug logs about configuration loading
- Should use the specified base URL
- Should show environment variable overrides in logs

### 10. API Integration Test (Backend Required)

**Steps**:
1. Make sure backend is running on localhost:8001
2. Login successfully
3. Click "Test API Call" button
4. Click "Test Token Refresh" button

**Expected Results**:
- API test should show token information
- Token refresh should succeed and update status
- Status should show success/failure messages

## What to Look For

### ✅ Good Signs
- Dialogs appear centered and properly sized
- Form validation works in real-time
- Loading states are clear and responsive
- Error messages are user-friendly
- UI updates immediately after auth state changes
- No crashes or freezing
- Console logs show appropriate debug information

### ⚠️ Issues to Report
- Dialogs appear off-screen or incorrectly sized
- Form validation not working or too strict
- Loading states stuck or not appearing
- Confusing error messages
- UI not updating after auth changes
- Application crashes or freezes
- Missing or excessive logging

## Common Issues and Solutions

### "Segmentation fault" on startup
- This usually means DearPyGUI can't initialize
- Try running with X11 forwarding if using SSH: `ssh -X`
- Make sure you have proper display environment

### "Connection refused" errors
- Make sure backend is running on port 8001
- Check `GOMOKU_BASE_URL` in .env file
- Verify firewall settings

### Form validation too strict/lenient
- Test edge cases with various input combinations
- Check that error messages are helpful
- Verify that valid inputs are accepted

## Reporting Results

When testing, please note:
1. **What worked well** - Which features functioned as expected
2. **Issues found** - Any bugs, crashes, or UX problems
3. **Suggestions** - Ideas for improvement
4. **Environment** - OS, Python version, display setup

This manual testing approach will give us much better validation of the actual user experience than mocked tests!