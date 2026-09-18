from fastapi import FastAPI


app = FastAPI(
    title="GridWise LLM Energy Optimizer",
    version="1.0.0"
)



@app.get("/health")
def health_check():

    return {
        "status": "ok"
    }