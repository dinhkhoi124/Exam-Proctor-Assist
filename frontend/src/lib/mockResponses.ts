// Mocked RAG-style responses for common exam issues

export interface MockResponse {
  keywords: string[];
  response: string;
  category: string;
}

export const mockResponses: MockResponse[] = [
  {
    keywords: ["wifi", "wi-fi", "wireless", "connect", "network", "internet"],
    category: "WiFi Issues",
    response: `**WiFi Connection Troubleshooting**

Here are the steps to resolve WiFi login issues:

1. **Check Network Name**: Ensure the student is connecting to "FPT-Exam" network (not FPT-Student or FPT-Guest)

2. **Verify Credentials**:
   - Username: Student ID (e.g., SE123456)
   - Password: Default exam password provided at the start

3. **Reset Connection**:
   - Turn WiFi off → Wait 10 seconds → Turn on again
   - Forget the network and reconnect

4. **Check IP Address**:
   - Open CMD → Type "ipconfig"
   - Should show 10.x.x.x range

5. **If still failing**: Contact IT Support at ext. **8888** or move student to a backup seat.

⚠️ **Important**: Do not allow students to use mobile hotspots during exams.`
  },
  {
    keywords: ["login", "password", "credential", "sign in", "signin", "account", "locked"],
    category: "Login Issues",
    response: `**Exam Portal Login Troubleshooting**

Follow these steps for login issues:

1. **Verify Student ID Format**:
   - Correct: SE123456 (uppercase letters)
   - Incorrect: se123456, SE-123456

2. **Password Reset**:
   - Click "Forgot Password" on exam portal
   - Student receives reset link to FPT email
   - Allow 2-3 minutes for email delivery

3. **Account Locked**:
   - After 5 failed attempts, account locks for 15 minutes
   - Contact Exam Office to unlock immediately: **ext. 7777**

4. **Browser Cache**:
   - Clear browser cache and cookies
   - Try Incognito/Private mode

5. **Alternative**: If urgent, Exam Office can provide temporary exam access code.`
  },
  {
    keywords: ["browser", "chrome", "firefox", "edge", "crash", "freeze", "slow"],
    category: "Browser Issues",
    response: `**Browser Troubleshooting**

Recommended browser: **Google Chrome** (latest version)

**Common Fixes**:

1. **Browser Crashes**:
   - Close all tabs except exam portal
   - Disable browser extensions
   - Clear cache: Ctrl + Shift + Delete

2. **Page Not Loading**:
   - Press F5 or Ctrl + R to refresh
   - Check internet connection
   - Try different browser as backup

3. **Slow Performance**:
   - Close other applications
   - Check if antivirus is scanning
   - Restart browser

4. **Compatibility Mode**:
   - Right-click browser → Properties
   - Uncheck "Run in compatibility mode"

⚠️ **Note**: Safari and Internet Explorer are NOT supported for exams.`
  },
  {
    keywords: ["exam", "portal", "system", "error", "500", "404", "page", "load"],
    category: "Exam Portal Issues",
    response: `**Exam Portal System Errors**

**Error Code Solutions**:

- **Error 404**: Page not found
  → Check URL: exam.fpt.edu.vn/exam
  → Do not use bookmarks from previous exams

- **Error 500**: Server error
  → Wait 30 seconds and refresh
  → If persists, contact IT: ext. **8888**

- **Error 503**: Service unavailable
  → System under maintenance or high load
  → Wait 2-3 minutes before retrying

- **Session Expired**:
  → Re-login with credentials
  → Do NOT click browser back button

**Emergency Protocol**: If portal is down for >5 minutes, contact Exam Office for paper-based backup.`
  },
  {
    keywords: ["time", "timer", "clock", "sync", "duration", "extend"],
    category: "Exam Timer Issues",
    response: `**Exam Timer Issues**

**Timer Not Showing**:
1. Refresh the page (F5)
2. Check if JavaScript is enabled in browser
3. Timer appears after clicking "Start Exam"

**Time Sync Issues**:
- Exam timer is server-based, not dependent on local time
- If local clock differs, exam still ends at correct time

**Requesting Time Extension**:
1. Document the technical issue with timestamp
2. Contact Exam Office: ext. **7777**
3. Provide student ID and reason
4. Extension approval takes 5-10 minutes

⚠️ **Note**: Only Exam Office can approve time extensions. Proctors cannot modify exam duration.`
  },
  {
    keywords: ["submit", "save", "upload", "file", "attachment", "answer"],
    category: "Submission Issues",
    response: `**Exam Submission Troubleshooting**

**Auto-Save Not Working**:
- Check internet connection
- Look for save indicator (green checkmark)
- Click "Save Draft" manually every 5 minutes

**File Upload Issues**:
- Maximum file size: 10MB
- Supported formats: PDF, DOC, DOCX, ZIP
- Rename file to: StudentID_Subject.pdf

**Submission Failed**:
1. Do NOT close the browser
2. Take screenshot of error
3. Try submitting again
4. If still failing, contact IT immediately

**After Time Expires**:
- System auto-submits last saved version
- Student cannot edit after deadline
- Late submissions require Exam Office approval

📞 **Emergency**: IT Support ext. **8888**`
  },
  {
    keywords: ["laptop", "computer", "screen", "display", "power", "battery", "charge"],
    category: "Hardware Issues",
    response: `**Laptop/Hardware Issues**

**Screen Issues**:
- Frozen screen: Ctrl + Alt + Delete → Task Manager
- Black screen: Check if laptop went to sleep (press any key)
- Brightness: Check Fn + brightness keys

**Power Issues**:
- Ensure laptop is plugged in during exam
- Battery should be >50% as backup
- Check power outlet is working

**Keyboard Not Working**:
- Check if NumLock/Caps Lock is on
- Try USB keyboard as backup (ask IT)
- On-screen keyboard: Windows key + Ctrl + O

**Emergency Power Failure**:
1. Note the time of failure
2. Exam progress auto-saved on server
3. Student can resume on backup laptop
4. Contact IT for device swap

🔌 **Backup laptops available in Room 101**`
  },
  {
    keywords: ["help", "support", "contact", "phone", "call", "emergency"],
    category: "Support Contacts",
    response: `**Emergency Support Contacts**

📞 **Quick Reference**:

| Department | Extension | Purpose |
|------------|-----------|---------|
| IT Support | 8888 | Technical issues |
| Exam Office | 7777 | Exam rules & extensions |
| Security | 9999 | Room emergencies |
| Building Mgmt | 6666 | Facilities issues |

**Response Times**:
- IT Support: 2-5 minutes
- Exam Office: 5-10 minutes

**Escalation Path**:
1. First: Try chatbot solutions
2. Then: Call relevant department
3. If no response in 10 min: Contact Exam Supervisor

**Physical Support**:
- IT Staff roaming: Building A, B, C
- Exam Office: Room A101`
  }
];

export const defaultResponse = `I understand you're experiencing an issue during the exam. Here's what I recommend:

1. **Describe the problem in more detail** - Include any error messages or specific symptoms

2. **Try these general steps**:
   - Refresh the page (F5)
   - Check internet connection
   - Clear browser cache

3. **If the issue persists**, please contact:
   - IT Support: ext. **8888**
   - Exam Office: ext. **7777**

I'm here to help! Please provide more details about the issue.`;

export function getMockResponse(message: string): string {
  const lowerMessage = message.toLowerCase();
  
  for (const mockResp of mockResponses) {
    if (mockResp.keywords.some(keyword => lowerMessage.includes(keyword))) {
      return mockResp.response;
    }
  }
  
  return defaultResponse;
}

export function getResponseCategory(message: string): string {
  const lowerMessage = message.toLowerCase();
  
  for (const mockResp of mockResponses) {
    if (mockResp.keywords.some(keyword => lowerMessage.includes(keyword))) {
      return mockResp.category;
    }
  }
  
  return "General Support";
}
