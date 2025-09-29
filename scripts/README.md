# Documentation Guide

Welcome to the Often Hotels API documentation. This directory contains comprehensive guides and documentation for all aspects of the application.

## 📚 Available Documentation

### API Documentation
- **[API Guide](./API_GUIDE.md)** - Complete API reference and usage examples
- **[Location Search API](./location-search-api.md)** - Unified location search with pagination and caching

### Integration Guides
- **[TravClan API Integration](./TRAVCLAN_API_INTEGRATION.md)** - External hotel booking API integration

### System Architecture
- **[Celery Deep Dive](./CELERY_DEEP_DIVE.md)** - Background task processing and scheduling
- **[System Explanation](./explanation.md)** - Overall system architecture and design

## 🚀 Quick Navigation

### For Developers
1. Start with [API Guide](./API_GUIDE.md) for general API usage
2. Check [Location Search API](./location-search-api.md) for search functionality
3. Review [System Explanation](./explanation.md) for architecture overview

### For Integrators
1. Read [TravClan API Integration](./TRAVCLAN_API_INTEGRATION.md) for external API details
2. Use [API Guide](./API_GUIDE.md) for authentication and endpoints

### For DevOps/Infrastructure
1. Review [Celery Deep Dive](./CELERY_DEEP_DIVE.md) for background task architecture
2. Check [System Explanation](./explanation.md) for deployment considerations

## 🔧 Development Workflow

1. **Local Development**: See main [README.md](../README.md) for setup instructions
2. **API Testing**: Use `/docs` endpoint for interactive API documentation
3. **Background Tasks**: Monitor with Celery Flower at `http://localhost:5555`
4. **Database**: Use admin tools or direct PostgreSQL connection

## 📖 Documentation Standards

All documentation in this directory follows:
- Clear structure with proper headings
- Code examples with syntax highlighting
- Step-by-step guides for complex processes
- Error handling and troubleshooting sections
- Performance considerations where applicable

---

For the most up-to-date information, always refer to the interactive API documentation at `/docs` when the application is running.