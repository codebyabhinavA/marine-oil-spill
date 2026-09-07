# Marine Oil Spill Intelligence System

This repository contains the initial project scaffold for the SIH 2026 challenge: Marine Oil Spill Intelligence System.

## Purpose
The system is designed to detect oil spills from satellite imagery, correlate them with environmental drift models and AIS vessel movements, and attribute the likely responsible vessel through a ranking pipeline.

## Major folders
- backend/: Python-based FastAPI backend, including data processing, modelling, routing, and persistence-ready data access layers.
- frontend/: React + TypeScript + Leaflet frontend for GIS visualization and dashboard interactions.
- docs/: Architecture notes, research references, and API documentation.
- tests/: Module-level test folders for satellite processing, drift modelling, AIS tracking, and attribution logic.

## Team organization
### Group 1
- Satellite Image Processing
- Oil Spill Detection AI

### Group 2
- Ocean & Oil Drift Modelling
- AIS & Vessel Tracking

### Group 3
- Vessel Attribution & Ranking
- Backend + GIS Dashboard

## Target workflow
Satellite -> Oil Spill Detection -> Drift/Hindcasting -> AIS -> Attribution -> Dashboard

## Notes
This is the initial scaffold only. Algorithms, services, and integrations will be implemented in future development stages.
