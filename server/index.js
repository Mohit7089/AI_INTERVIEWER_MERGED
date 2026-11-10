import express from "express"
import dotenv from "dotenv"
import connectDb from "./config/connectDb.js"
import cookieParser from "cookie-parser"
dotenv.config()
import cors from "cors"
import authRouter from "./routes/auth.route.js"
import userRouter from "./routes/user.route.js"
import interviewRouter from './routes/interview.route.js';

const app=express()
app.use(cors({
    origin:"http://localhost:5173",
    credentials:true
}))

app.use(express.json())
app.use(cookieParser())

app.use("/api/auth", authRouter)
app.use("/api/user", userRouter)
app.use("/api/interview" , interviewRouter)
// app.use("/api/payment" , paymentRouter)

console.log("API KEY:", process.env.OPENROUTER_API_KEY);
const PORT=process.env.PORT || 4000
app.listen(PORT, ()=>{
    console.log(`Server running on port ${PORT}`)
    connectDb()
})

