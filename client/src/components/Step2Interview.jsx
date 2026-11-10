import React from 'react'
import maleVideo from "../assets/videos/male-ai.mp4"
import femaleVideo from "../assets/videos/female-ai.mp4"
import Timer from './Timer'
import { motion } from "motion/react"
import { FaMicrophone, FaMicrophoneSlash } from "react-icons/fa";
import  { useState, useRef, useEffect } from 'react';
import axios from "axios"
import { ServerUrl } from '../App'
import { BsArrowRight } from 'react-icons/bs'
import { useSelector } from 'react-redux'
import ProctoringPanel from './ProctoringPanel'
import { useProctoring } from "../hooks/useProctoring";


function Step2Interview({ interviewData, onFinish }) {
  const userData = useSelector((state) => state.user.userData)
  const [score, setScore] = useState(null);
 const [totalScore, setTotalScore] = useState(0);
  const { interviewId, questions, userName } = interviewData;
  const [isIntroPhase, setIsIntroPhase] = useState(true);

  const [isMicOn, setIsMicOn] = useState(true);
  
  const recognitionRef = useRef(null);
  const [isAIPlaying, setIsAIPlaying] = useState(false);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState("");
  const [timeLeft, setTimeLeft] = useState(
    questions[0]?.timeLimit || 90
  );
  const [selectedVoice, setSelectedVoice] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [voiceGender, setVoiceGender] = useState("female");
  const [subtitle, setSubtitle] = useState("");
  const [followUpCount, setFollowUpCount] = useState(0);

  const [dynamicQuestion, setDynamicQuestion] = useState(null);
  const isMicOnRef = useRef(true);

  
  // ── Audio confidence recording refs ─────────────────────────────────────
  const streamRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const isAudioRecordingRef = useRef(false); // whether a recorder exists for the current question


  const videoRef = useRef(null);
  const currentQuestion = dynamicQuestion || questions[currentIndex];

  const {
    videoRef: proctorVideoRef,
    canvasRef: proctorCanvasRef,
    status: proctorStatus,
    isConnected: proctorConnected,
    latestResult: proctorLatestResult,
    activeWarning: proctorActiveWarning,
    error: proctorError,
    endSession,
  } = useProctoring({
    interviewId,
    userId: userData?._id,
    candidateName: userName,
    active: !isIntroPhase,
    onReportReady: (report) => console.log('Proctoring report:', report),
  });

  useEffect(() => {
    const loadVoices = () => {
      const voices = window.speechSynthesis.getVoices();
      if (!voices.length) return;
      

      // Try known female voices first
      const femaleVoice =
        voices.find(v =>
          v.name.toLowerCase().includes("zira") ||
          v.name.toLowerCase().includes("samantha") ||
          v.name.toLowerCase().includes("female")
        );

      if (femaleVoice) {
        setSelectedVoice(femaleVoice);
        setVoiceGender("female");
        return;
      }

      // Try known male voices
      const maleVoice =
        voices.find(v =>
          v.name.toLowerCase().includes("david") ||
          v.name.toLowerCase().includes("mark") ||
          v.name.toLowerCase().includes("male")
        );

      if (maleVoice) {
        setSelectedVoice(maleVoice);
        setVoiceGender("male");
        return;
      }

      // Fallback: first voice (assume female)
      setSelectedVoice(voices[0]);
      setVoiceGender("female");
    };

    loadVoices();
    window.speechSynthesis.onvoiceschanged = loadVoices;

  }, [])
   useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);

  const videoSource = voiceGender === "male" ? maleVideo : femaleVideo;

  // ── Acquire mic stream once on mount (used for MediaRecorder, separate
  //    from webkitSpeechRecognition which grabs its own internal stream) ──
  useEffect(() => {
    navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    }).then(stream => {
      streamRef.current = stream;
    }).catch(err => console.log("Mic permission error:", err));

    return () => {
      streamRef.current?.getTracks().forEach(t => t.stop());
    };
  }, []);

  // ── Start a fresh recorder for a new question ───────────────────────────
  const startAudioRecording = () => {
    if (!streamRef.current) return;
    if (isAudioRecordingRef.current) return; // already recording this question

    audioChunksRef.current = [];
    const recorder = new MediaRecorder(streamRef.current, { mimeType: "audio/webm" });
    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunksRef.current.push(e.data);
    };
    recorder.start();
    mediaRecorderRef.current = recorder;
    isAudioRecordingRef.current = true;
  };

  // ── Pause/resume around AI-speaking gaps, so one question = one blob ───
  const pauseAudioRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.pause();
    }
  };

  const resumeAudioRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "paused") {
      mediaRecorderRef.current.resume();
    }
  };

  // ── Stop recording and return the finished blob for this question ──────
  const stopAudioRecordingAndGetBlob = () => {
    return new Promise((resolve) => {
      if (!mediaRecorderRef.current || !isAudioRecordingRef.current) {
        resolve(null);
        return;
      }
      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        audioChunksRef.current = [];
        isAudioRecordingRef.current = false;
        resolve(blob);
      };
      mediaRecorderRef.current.stop();
    });
  };

  // ── Upload the answer's audio blob for confidence analysis ─────────────
  const submitAudioForConfidence = async (blob, questionId) => {
    if (!blob || blob.size === 0) return;
    try {
      const formData = new FormData();
      formData.append("audio", blob, `answer_${Date.now()}.webm`);
      formData.append("interviewId", interviewId);
      // formData.append("questionId", questionId);
      formData.append("question", currentQuestion.question); 

      await axios.post(ServerUrl + "/api/interview/submit-audio", formData, {
        withCredentials: true,
        headers: { "Content-Type": "multipart/form-data" }
      });
    } catch (err) {
      // Non-fatal: confidence analysis failing shouldn't block the interview flow
      console.log("Audio confidence upload failed:", err);
    }
  };

  /* ---------------- SPEAK FUNCTION ---------------- */
  const speakText = (text) => {
    return new Promise((resolve) => {
      if (!window.speechSynthesis || !selectedVoice) {
        resolve();
        return;
      }

      window.speechSynthesis.cancel();

      // Add natural pauses after commas and periods
      const humanText = text
        .replace(/,/g, ", ... ")
        .replace(/\./g, ". ... ");

      const utterance = new SpeechSynthesisUtterance(humanText);

      utterance.voice = selectedVoice;

      // Human-like pacing
      utterance.rate = 0.92;     // slightly slower than normal
      utterance.pitch = 1.05;    // small warmth
      utterance.volume = 1;

      utterance.onstart = () => {
        setIsAIPlaying(true);
        stopMic()
        videoRef.current?.play();
      };


      utterance.onend = () => {
        videoRef.current?.pause();
        videoRef.current.currentTime = 0;
        setIsAIPlaying(false);



        if (isMicOn) {
          startMic();
        }
        setTimeout(() => {
          setSubtitle("");
          resolve();
        }, 300);
      };


      setSubtitle(text);

      window.speechSynthesis.speak(utterance);
    });
  };


  useEffect(() => {
    if (!selectedVoice) {
      return;
    }
    const runIntro = async () => {
      if (isIntroPhase) {
        await speakText(
          `Hi ${userName}, it's great to meet you today. I hope you're feeling confident and ready.`
        );

        await speakText(
          "I'll ask you a few questions. Just answer naturally, and take your time. Let's begin."
        );

        setIsIntroPhase(false)
      } else if (currentQuestion) {
        await new Promise(r => setTimeout(r, 800));

        // If last question (hard level)
        if (currentIndex === questions.length - 1) {
          await speakText("Alright, this one might be a bit more challenging.");
        }

        await speakText(currentQuestion.question);

        if (isMicOn) {
          startMic();
        }
      }

    }

    runIntro()


  }
  , [selectedVoice, isIntroPhase, currentIndex, dynamicQuestion])
  useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);



  useEffect(() => {
    if (isIntroPhase) return;
    if (!currentQuestion) return;

    
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          return 0;
        }
        return prev - 1

      })
    }, 1000);

    return () => clearInterval(timer)

  }, [isIntroPhase, currentIndex , dynamicQuestion])
  useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);

useEffect(() => {
  if (isIntroPhase) return;
  if (!currentQuestion) return;

  setTimeLeft(currentQuestion.timeLimit || 90);

  const timer = setInterval(() => {
    setTimeLeft(prev => {
      if (prev <= 1) {
        clearInterval(timer);
        return 0;
      }
      return prev - 1;
    });
  }, 1000);

  return () => clearInterval(timer);

}, [currentIndex, dynamicQuestion]);
useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);


  useEffect(() => {
    if (!("webkitSpeechRecognition" in window)) return;

    const recognition = new window.webkitSpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
      const transcript =
        event.results[event.results.length - 1][0].transcript;

      setAnswer((prev) => prev + " " + transcript);
    };
recognition.onend = () => {
  if (!isMicOnRef.current) return;

  setTimeout(() => {
    try {
      recognition.start();
    } catch (err) {}
  }, 300);
};

    recognitionRef.current = recognition;

  }, []);
  useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);


  const startMic = () => {
    if (recognitionRef.current && !isAIPlaying) {
      try {
        recognitionRef.current.start();
      } catch { }
    }
    // Audio recording: start fresh for a new question, resume if just paused
    // for an AI-speaking gap within the same question.
    if (!isAudioRecordingRef.current) {
      startAudioRecording();
    } else {
      resumeAudioRecording();
    }
  };

  const stopMic = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    // Pause (not stop) so the question's audio stays a single clip —
    // actual stop only happens at submitAnswer/finishInterview time.
    pauseAudioRecording();
  };
  const toggleMic = () => {
    if (isMicOn) {
      stopMic();
    } else {
      startMic();
    }
    setIsMicOn(!isMicOn);
  };


  const submitAnswer = async () => {
    
    if (isSubmitting) return;
    stopMic()
    setIsSubmitting(true)

    // Finalize this question's audio clip and send it for confidence analysis
    // (fire-and-forget — doesn't block the score/feedback flow below)
    const questionIdForAudio = currentQuestion?.id ?? currentQuestion?.question;
    stopAudioRecordingAndGetBlob().then((blob) => {
      submitAudioForConfidence(blob, questionIdForAudio);
    });

    try {
      const result = await axios.post(ServerUrl + "/api/interview/submit-answer", {
  interviewId,
  question: currentQuestion.question,
  answer,
  timeTaken: currentQuestion.timeLimit - timeLeft,
  keywords: currentQuestion.keywords || []
}, { withCredentials: true })

// ✅ Score the current question FIRST
setScore(result.data.score);
setTotalScore(prev => prev + result.data.score);

// Then show follow-up if there is one
if (result.data.nextQuestion && followUpCount < 1) {

  setDynamicQuestion({
    id: Date.now(),
    question: result.data.nextQuestion,
    timeLimit: 90,
    keywords: currentQuestion.keywords || []
  });

  setFollowUpCount(prev => prev + 1);

  setAnswer("");
  setFeedback("");
  setTimeLeft(90);

  setTimeout(() => {
    if (isMicOn) startMic();
  }, 500);

  setIsSubmitting(false);
  return;
}

setScore(result.data.score); // current question
setTotalScore(prev => prev + result.data.score); // total score
// setFeedback(result.data.feedback);
// await speakText(result.data.feedback);
handleNext();
setIsSubmitting(false);
    } catch (error) {
console.log(error)
setIsSubmitting(false)
    }
  }

const handleNext = async () => {
  setAnswer("");
  setFeedback("");

  // 🔥 FOLLOW-UP CASE
  if (dynamicQuestion) {
    setDynamicQuestion(null);
    setFollowUpCount(0);

    // move to next MAIN question
    if (currentIndex + 1 >= questions.length) {
      finishInterview();
      return;
    }

    setCurrentIndex(prev => prev + 1);
    return;
  }

  // 🔥 NORMAL FLOW
  if (currentIndex >= questions.length - 1) {
    finishInterview();
    return;
  }

  setCurrentIndex(prev => prev + 1);
};

  const finishInterview = async () => {
    stopMic()
    setIsMicOn(false)
    await endSession();    // ← finalize proctoring, wait for report before navigating away
    try {
      const result = await axios.post(ServerUrl+ "/api/interview/finish" , { interviewId} , {withCredentials:true})

      console.log(result.data)
      onFinish(result.data)
    } catch (error) {
      console.log(error)
    }
  }


useEffect(() => {
  if (isIntroPhase) return;
  if (!currentQuestion) return;

  // 🔥 ADD THIS
  if (dynamicQuestion) return;

  if (timeLeft === 0 && !isSubmitting && !feedback) {
    submitAnswer();
  }
}
, [timeLeft]);
useEffect(() => {
  isMicOnRef.current = isMicOn;
}, [isMicOn]);

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current.abort();
      }

      window.speechSynthesis.cancel();
    };
  }, []);
  useEffect(() => {
  if (currentIndex >= questions.length) {
    finishInterview();
  }
}, [currentIndex]);







  return (
    <div className='min-h-screen bg-linear-to-br from-emerald-50 via-white to-teal-100 flex items-center justify-center p-4 sm:p-6'>
      <div className='w-full max-w-350 min-h-[80vh] bg-white rounded-3xl shadow-2xl border border-gray-200 flex flex-col lg:flex-row overflow-hidden'>

        {/* video section */}
        <div className='w-full lg:w-[35%] bg-white flex flex-col items-center p-6 space-y-6 border-r border-gray-200'>
          <div className='w-full max-w-md rounded-2xl overflow-hidden shadow-xl'>
            <video
              src={videoSource}
              key={videoSource}
              ref={videoRef}
              muted
              playsInline
              preload="auto"
              className="w-full h-auto object-cover"
            />
          </div>

          {/* subtitle */}
          {subtitle && (
            <div className='w-full max-w-md bg-gray-50 border border-gray-200 rounded-xl p-4 shadow-sm'>
              <p className='text-gray-700 text-sm sm:text-base font-medium text-center leading-relaxed'>{subtitle}</p>
            </div>
          )}


          {/* timer Area */}
          <div className='w-full max-w-md bg-white border border-gray-200 rounded-2xl shadow-md p-6 space-y-5'>
            <div className='flex justify-between items-center'>
              <span className='text-sm text-gray-500'>
                Interview Status
              </span>
              {isAIPlaying && <span className='text-sm font-semibold text-emerald-600'>
                {isAIPlaying ? "AI Speaking" : ""}
              </span>}
            </div>

            <div className="h-px bg-gray-200"></div>

            <div className='flex justify-center'>

              <Timer timeLeft={timeLeft} totalTime={currentQuestion?.timeLimit} />
            </div>

            <div className="h-px bg-gray-200"></div>

            <div className='grid grid-cols-2 gap-6 text-center'>
              <div>
                <span className='text-2xl font-bold text-emerald-600'>{currentIndex + 1}</span>
                <span className='text-xs text-gray-400'>Current Questions</span>
              </div>

              <div>
                <span className='text-2xl font-bold text-emerald-600'>{questions.length}</span>
                <span className='text-xs text-gray-400'>Total Questions</span>
              </div>
            </div>


          </div>
        </div>

        {/* Text section */}

        <div className='flex-1 flex flex-col p-4 sm:p-6 md:p-8 relative'>
          <h2 className='text-xl sm:text-2xl font-bold text-emerald-600 mb-6'>
            AI Smart Interview
          </h2>


          {!isIntroPhase && (<div className='relative mb-6 bg-gray-50 p-4 sm:p-6 rounded-2xl border border-gray-200 shadow-sm'>
            <p className='text-xs sm:text-sm text-gray-400 mb-2'>
              Question {currentIndex + 1} of {questions.length}
            </p>

            <div className='text-base sm:text-lg font-semibold text-gray-800 leading-relaxed '>{currentQuestion?.question}</div>
          </div>)
          }
          <textarea
            placeholder="Type your answer here..."
            onChange={(e) => setAnswer(e.target.value)}
            value={answer}
            className="flex-1 bg-gray-100 p-4 sm:p-6 rounded-2xl resize-none outline-none border border-gray-200 focus:ring-2 focus:ring-emerald-500 transition text-gray-800" />


         {(!feedback || dynamicQuestion) ? ( <div className='flex items-center gap-4 mt-6'>
<p className="text-sm text-gray-600 mb-3">
  Total Score: {totalScore} / {questions.length * 10}
</p>
            <motion.button
              onClick={toggleMic}
              whileTap={{ scale: 0.9 }}
              className='w-12 h-12 sm:w-14 sm:h-14 flex items-center justify-center rounded-full bg-black text-white shadow-lg'>
              {isMicOn ? <FaMicrophone size={20} /> : <FaMicrophoneSlash size={20}/>}
            </motion.button>

            <motion.button
            onClick={submitAnswer}
            disabled={isSubmitting}
              whileTap={{ scale: 0.95 }}
              className='flex-1 bg-gradient-to-r from-emerald-600 to-teal-500 text-white py-3 sm:py-4 rounded-2xl shadow-lg hover:opacity-90 transition font-semibold disabled:bg-gray-500'>
              {isSubmitting?"Submitting...":"Submit Answer"}

            </motion.button>

          </div>):(
            <motion.div 
             initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            className='mt-6 bg-emerald-50 border border-emerald-200 p-5 rounded-2xl shadow-sm'>
              <p className='text-emerald-700 font-medium mb-4'>{feedback}</p>

              <button
              onClick={handleNext}

               className='w-full bg-gradient-to-r from-emerald-600 to-teal-500 text-white py-3 rounded-xl shadow-md hover:opacity-90 transition flex items-center justify-center gap-1'>
                Next Question <BsArrowRight size={18}/>
              </button>

            </motion.div>
          )}
        </div>
      </div>

      <ProctoringPanel
        videoRef={proctorVideoRef}
        canvasRef={proctorCanvasRef}
        status={proctorStatus}
        isConnected={proctorConnected}
        latestResult={proctorLatestResult}
        activeWarning={proctorActiveWarning}
        error={proctorError}
      />

    </div>
  )
}

export default Step2Interview
