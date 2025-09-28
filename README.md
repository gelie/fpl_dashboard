# Fantasy Premier League Dashboard

A modern, responsive web application for tracking Fantasy Premier League scores and performance built with FastAPI and deployed on Vercel.

## 🚀 Features

- **Dashboard**: Interactive charts showing weekly and overall team performance
- **Player Management**: Add, edit, and delete players with team associations
- **Score Tracking**: Bulk entry system for gameweek scores with automatic calculations
- **Authentication**: HTTP Basic Auth for admin functions
- **Responsive Design**: Mobile-first design that works on all devices
- **Real-time Updates**: Automatic overall points calculation and cumulative tracking

## 📱 Responsive Design

- **Mobile Navigation**: Collapsible hamburger menu for mobile devices
- **Touch-Friendly**: Optimized buttons and inputs for touch interfaces
- **Adaptive Tables**: Horizontal scrolling on mobile with proper touch scrolling
- **Flexible Charts**: Charts resize automatically for different screen sizes
- **Progressive Enhancement**: Works on all devices from mobile to desktop

## 🛠 Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML5, CSS3 (Pico CSS), Vanilla JavaScript
- **Database**: SQLModel with SQLite
- **Charts**: Chart.js for data visualization
- **Deployment**: Vercel (Serverless)
- **Authentication**: HTTP Basic Auth

## 🚀 Deployment on Vercel

### Prerequisites

1. **Vercel Account**: Sign up at [vercel.com](https://vercel.com)
2. **Git Repository**: Push your code to GitHub, GitLab, or Bitbucket

### Quick Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/fpl-dashboard)

### Manual Deployment Steps

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd fpl_dashboard
   ```

2. **Install Vercel CLI** (optional):
   ```bash
   npm i -g vercel
   ```

3. **Deploy via Vercel Dashboard**:
   - Go to [vercel.com/dashboard](https://vercel.com/dashboard)
   - Click "New Project"
   - Import your Git repository
   - Vercel will automatically detect the configuration

4. **Deploy via CLI**:
   ```bash
   vercel --prod
   ```

### Environment Variables

Set these environment variables in your Vercel dashboard:

```env
ADMIN_USERNAME=your_admin_username
ADMIN_PASSWORD=your_admin_password
```

**To set environment variables**:
1. Go to your project dashboard on Vercel
2. Navigate to Settings → Environment Variables
3. Add the variables above

### Vercel Configuration

The project includes a `vercel.json` file with the following configuration:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/static/(.*)",
      "dest": "/static/$1"
    },
    {
      "src": "/(.*)",
      "dest": "/main.py"
    }
  ]
}
```

## 🏃‍♂️ Local Development

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Create `.env` file**:
   ```env
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=your_password
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

4. **Open browser**: Navigate to `http://localhost:8000`

## 📊 Usage

### For Viewers (Anonymous Users)
- Browse all data without authentication
- View dashboard charts and statistics
- Filter scores by player and gameweek
- See "View Only" status in action columns

### For Admins (Authenticated Users)
1. **Login**: Click "Admin Login" and enter credentials
2. **Add Players**: Use the player management interface
3. **Add Scores**: Use the bulk entry form for efficient gameweek data entry
4. **Edit/Delete**: Modify existing data as needed

### Bulk Score Entry
- Click "Add Scores for GW X" (X = next gameweek)
- Enter points and costs for each team in the table
- Leave fields empty for teams that didn't play
- Submit once to process all scores

## 🔧 Configuration

### Database
- Uses SQLite by default (perfect for Vercel)
- Database file is created automatically
- No additional setup required

### Authentication
- HTTP Basic Authentication
- Credentials stored in environment variables
- Session persists until logout or browser close

### Charts
- Powered by Chart.js
- Responsive and interactive
- Shows weekly points and cumulative performance

## 📱 Mobile Features

- **Hamburger Menu**: Tap ☰ to access navigation
- **Touch Scrolling**: Swipe to scroll tables horizontally
- **Responsive Forms**: Inputs adapt to screen size
- **Touch Targets**: Buttons sized appropriately for fingers

## 🔒 Security

- Admin functions protected by HTTP Basic Auth
- Environment variables for sensitive data
- No client-side credential storage
- HTTPS enforced on Vercel

## 🐛 Troubleshooting

### Common Issues

1. **Authentication not working**:
   - Check environment variables are set correctly
   - Ensure ADMIN_USERNAME and ADMIN_PASSWORD are configured

2. **Static files not loading**:
   - Verify static files are in the `/static/` directory
   - Check Vercel routes configuration

3. **Database issues**:
   - SQLite database is created automatically
   - No manual database setup required

### Vercel-Specific Issues

1. **Build failures**:
   - Check `requirements.txt` has all dependencies
   - Ensure Python version compatibility

2. **Function timeout**:
   - Vercel has a 10-second timeout for serverless functions
   - Consider optimizing database queries if needed

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🎯 Live Demo

Once deployed, your app will be available at: `https://your-project-name.vercel.app`

---

**Built with ❤️ using FastAPI and deployed on Vercel**