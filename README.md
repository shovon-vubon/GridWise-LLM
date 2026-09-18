# GridWise-LLM: AI-Powered Energy Optimization System

## Overview

GridWise-LLM is an intelligent energy management system that combines:

- Large Language Models (LLMs)
- Deterministic validation
- Mathematical optimization

to convert human operator instructions into safe and optimized energy schedules.

The system understands natural language energy directives such as:

- "Reduce solar output to 30% between 1 PM and 3 PM"
- "Maintain 100 kWh battery reserve after 6 PM"
- "Do not charge the battery during peak hours"

and converts them into structured machine-readable constraints.

The validated constraints are then passed to an optimization engine to generate an efficient energy schedule.

---

# System Architecture

```
Operator Notes
      |
      |
      v
+----------------+
| LLM Interpreter|
| Groq Primary   |
| Gemini Backup  |
+----------------+
      |
      |
      v
Structured JSON Directives
      |
      |
      v
+----------------+
| Validator      |
| Safety Layer   |
+----------------+
      |
      |
      v
+----------------+
| OR-Tools       |
| Optimizer      |
+----------------+
      |
      |
      v
Optimized Energy Schedule
```

---

# Key Features

## 1. Natural Language Understanding

The system uses LLMs to understand operator instructions.

Supported examples:

```
"Solar generation will reduce to 40% from noon to 2 PM."
```

Converted into:

```json
{
 "directive_type":"solar_reduction",
 "structured_adjustment":{
    "hours":[12,13],
    "factor":0.4
 }
}
```

---

## 2. Multi-Provider LLM Fallback

The system uses:

Primary:

```
Groq API
```

Backup:

```
Google Gemini API
```

Flow:

```
Groq
 |
Failure
 |
Gemini
```

This improves reliability during deployment.

---

## 3. Directive Validation

LLM outputs are never directly sent to the optimizer.

The validator checks:

- Allowed directive types
- Valid hours
- Numeric ranges
- Required parameters
- Invalid outputs

Supported directives:

```
solar_reduction

minimum_battery_reserve

no_charge_window

no_discharge_window

max_grid_window

no_op
```

---

## 4. Optimization Engine

The optimization engine generates feasible schedules while considering:

- Electricity demand
- Solar generation
- Battery capacity
- Charging limits
- Discharging limits
- Grid constraints
- Operator rules


Optimization objectives:

```
Minimize:

Energy Cost

+

Constraint Violations
```

---

# Technology Stack

## Backend

- Python
- FastAPI

## AI

- Groq LLM API
- Google Gemini API

## Optimization

- Google OR-Tools

## Deployment

- Render

---

# Project Structure

```
GridWise-LLM

│
├── app
│   |
│   ├── main.py
│   ├── config.py
│   ├── schemas.py
│   |
│   ├── llm
│   │   ├── interpreter.py
│   │   └── prompts.py
│   |
│   ├── validators
│   │   └── directive_validator.py
│   |
│   └── optimizer
│       ├── energy_optimizer.py
│       └── constraints.py
│
├── requirements.txt
├── .env
├── Dockerfile
└── README.md
```

---

# Installation

## 1. Clone repository

```bash
git clone <repository-url>

cd GridWise-LLM
```

---

## 2. Create virtual environment

```bash
python -m venv venv
```

Activate:

Windows:

```powershell
venv\Scripts\activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# Environment Variables

Create:

```
.env
```

Add:

```env
GROQ_API_KEY=your_groq_key

GROQ_MODEL=llama-3.1-8b-instant


GEMINI_API_KEY=your_gemini_key

GEMINI_MODEL=gemini-3.6-flash
```

---

# Running Locally

Start FastAPI:

```bash
uvicorn app.main:app --reload
```

Open:

```
http://127.0.0.1:8000/docs
```

Swagger documentation will appear.

---

# API Endpoints

## 1. Test LLM Interpretation

Endpoint:

```
POST /test-llm
```

Purpose:

Tests natural language understanding.

---

## 2. Optimize Energy Schedule

Endpoint:

```
POST /optimize-energy
```

Complete pipeline:

```
Notes
 |
LLM
 |
Validator
 |
Optimizer
 |
Schedule
```

---

# API Test Cases

## Test Case 1 — Solar Reduction

### Input

```json
{
 "notes":[
   "Solar output will drop to 20% from 1 PM to 3 PM."
 ]
}
```

### Expected Answer

```json
{
 "directives":[
  {
   "note_index":0,
   "applies":true,
   "directive_type":"solar_reduction",
   "structured_adjustment":{
      "hours":[13,14],
      "factor":0.2
   }
  }
 ]
}
```

---

# Test Case 2 — Battery Reserve

### Input

```json
{
 "notes":[
   "Keep 150 kWh battery reserve after 6 PM."
 ]
}
```

### Expected Answer

```json
{
 "directives":[
  {
   "directive_type":"minimum_battery_reserve",
   "structured_adjustment":{
      "hours":[18,19,20,21,22,23],
      "minimum_energy_kwh":150
   }
  }
 ]
}
```

---

# Test Case 3 — No Charging Window

### Input

```json
{
 "notes":[
   "Battery charging is unavailable between noon and 2 PM."
 ]
}
```

### Expected Answer

```json
{
 "directive_type":"no_charge_window",

 "structured_adjustment":{
    "hours":[12,13]
 }
}
```

---

# Test Case 4 — Maximum Grid Import

### Input

```json
{
 "notes":[
   "Grid import must remain below 200 kWh from 6 PM to 8 PM."
 ]
}
```

### Expected Answer

```json
{
 "directive_type":"max_grid_window",

 "structured_adjustment":{
    "hours":[18,19],
    "max_grid_kwh":200
 }
}
```

---

# Test Case 5 — Irrelevant Note

### Input

```json
{
 "notes":[
   "The football match has been postponed."
 ]
}
```

### Expected Answer

```json
{
 "directive_type":"no_op",

 "applies":false,

 "structured_adjustment":null
}
```

---

# Full Optimization Test

## Request

```json
{
 "scenario_id":"campus_demo_001",

 "operator_notes":[
   "Solar output will reduce to 40% from 1 PM to 3 PM.",
   "Keep 100 kWh reserve after 6 PM.",
   "No battery charging between noon and 2 PM."
 ],

 "battery":{
   "capacity_kwh":800,
   "initial_energy_kwh":350,
   "minimum_energy_kwh":100,
   "max_charge_kwh_per_hour":150,
   "max_discharge_kwh_per_hour":200
 }
}
```

---

## Expected System Behaviour

The optimizer should:

- Use solar generation whenever available
- Avoid charging during restricted hours
- Maintain battery reserve
- Discharge battery during expensive grid periods
- Reduce total energy cost

---

# Deployment

## Render Configuration

Build Command:

```
pip install -r requirements.txt
```

Start Command:

```
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Environment variables should be added in Render dashboard.

---

# Future Improvements

Possible extensions:

- Firebase history storage
- User dashboard
- Real-time energy monitoring
- Weather-based solar prediction
- Reinforcement learning optimization

---

# License

Developed for the GridWise Energy Optimization Challenge.
