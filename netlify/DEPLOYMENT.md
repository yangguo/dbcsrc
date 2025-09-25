# Netlify Deployment Guide

## Prerequisites
1. Install Netlify CLI: `npm install -g netlify-cli`
2. Create a Netlify account at https://netlify.com

## Deployment Steps

### Option 1: Deploy with Netlify CLI (Recommended)
1. Login to Netlify: `netlify login`
2. Initialize project: `netlify init`
3. Set environment variables in Netlify dashboard:
   - MONGODB_URI (required)
   - MONGODB_DB (optional, defaults to 'pencsrc2')
   - MONGODB_COLLECTION (optional, defaults to 'csrc2analysis')
4. Deploy: `netlify deploy --prod`

### Option 2: Deploy via Git
1. Push your code to a Git repository (GitHub, GitLab, or Bitbucket)
2. Connect your repository to Netlify:
   - Go to https://app.netlify.com
   - Click "New site from Git"
   - Select your repository
   - Set build settings:
     - Build command: `next build`
     - Publish directory: `.next`
   - Add environment variables in the "Environment variables" section
   - Click "Deploy site"

## Environment Variables
You must set the following environment variables in the Netlify dashboard:

- `MONGODB_URI`: Your MongoDB connection string
- `MONGODB_DB`: (Optional) Database name, defaults to 'pencsrc2'
- `MONGODB_COLLECTION`: (Optional) Collection name, defaults to 'csrc2analysis'

## Notes
- Next.js API routes work automatically with Netlify Functions
- The application will be deployed as a serverless application
- Netlify will automatically handle the build process