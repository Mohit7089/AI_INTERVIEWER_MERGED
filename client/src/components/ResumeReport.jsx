import React from "react";
import { 
  FaArrowLeft, 
  FaRocket, 
  FaExclamationTriangle, 
  FaCheckCircle, 
  FaLightbulb, 
  FaLaptopCode, 
  FaFolderOpen,
  FaEnvelope,
  FaPhone,
  FaGithub,
  FaLinkedin
} from "react-icons/fa";
import { CircularProgressbar, buildStyles } from "react-circular-progressbar";
import { useNavigate, useLocation } from "react-router-dom";

function ResumeReport() {
  const navigate = useNavigate();
  const location = useLocation();

  const report = location.state?.report;

  if (!report) {
    return (
      <div className="min-h-screen flex justify-center items-center bg-slate-50">
        <p className="text-base text-slate-600 font-medium bg-white px-6 py-4 rounded-xl shadow-sm border">
          No resume report found. Please upload a resume first.
        </p>
      </div>
    );
  }

  const {
    score,
    atsScore,
    role,
    summary,
    skills = [],
    topSkills = [],
    missingSkills = [],
    strengths = [],
    weaknesses = [],
    suggestions = [],
    careerRecommendation = [],
    contact = {},
    projects = []
  } = report;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 antialiased text-sm md:text-base">
      
      {/* Header */}
      <div className="bg-white border-b border-slate-200 sticky top-0 z-50 shadow-sm backdrop-blur-md bg-white/95">
        <div className="max-w-screen-xl mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-4">
            <button
              onClick={() => {
    navigate("/interview", {
        state: location.state
    });
}}
              className="w-10 h-10 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition flex items-center justify-center text-sm"
            >
              <FaArrowLeft />
            </button>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900">
                Resume Analysis Dashboard
              </h1>
              <p className="text-xs md:text-sm text-slate-500 font-medium mt-0.5">
                AI Powered ATS Analytics Engine
              </p>
            </div>
          </div>
          <div className="hidden sm:block">
            <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 px-4 py-1.5 rounded-xl text-xs md:text-sm font-semibold tracking-wide">
              System Ready
            </span>
          </div>
        </div>
      </div>

      <div className="max-w-screen-xl mx-auto p-6 space-y-6">
        
        {/* Top Cards: Scores & Match */}
        <div className="grid md:grid-cols-3 gap-5">
          
          {/* Resume Score */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 flex items-center justify-between shadow-sm">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">Resume Score</span>
              <h3 className="text-xl font-extrabold text-slate-800 mt-1">Overall Quality</h3>
            </div>
            <div className="w-24 h-24 font-bold">
              <CircularProgressbar
                value={score}
                text={`${score}%`}
                styles={buildStyles({
                  pathColor: "#10b981",
                  textColor: "#0f172a",
                  trailColor: "#f1f5f9",
                  textSize: "22px"
                })}
              />
            </div>
          </div>

          {/* ATS Score */}
          <div className="rounded-2xl border border-slate-200 bg-white p-5 flex items-center justify-between shadow-sm">
            <div>
              <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">ATS Compatibility</span>
              <h3 className="text-xl font-extrabold text-slate-800 mt-1">Parser Friendly</h3>
            </div>
            <div className="w-24 h-24 font-bold">
              <CircularProgressbar
                value={atsScore}
                text={`${atsScore}%`}
                styles={buildStyles({
                  pathColor: "#3b82f6",
                  textColor: "#0f172a",
                  trailColor: "#f1f5f9",
                  textSize: "22px"
                })}
              />
            </div>
          </div>

          {/* Best Match Role */}
          <div className="rounded-2xl border border-slate-200 bg-slate-900 text-white p-5 flex flex-col justify-between shadow-sm relative overflow-hidden group">
            <div className="absolute -right-6 -bottom-6 text-slate-800 opacity-20 text-8xl font-bold select-none pointer-events-none">AI</div>
            <div>
              <span className="text-[11px] font-bold uppercase tracking-widest text-indigo-400">Best Match Profile</span>
              <h2 className="text-xl md:text-2xl font-extrabold tracking-tight mt-1 truncate">{role}</h2>
            </div>
            <div className="mt-4 bg-white/10 text-slate-200 text-xs md:text-sm rounded-lg px-3 py-1.5 w-fit border border-white/10 font-medium">
              Target Blueprint Verified
            </div>
          </div>
        </div>

        {/* Summary & Contact */}
        <div className="grid lg:grid-cols-3 gap-5">
          
          {/* Summary */}
          <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100 flex items-center gap-2">
              <span className="w-1.5 h-4 bg-indigo-600 rounded-sm"></span> AI Executive Summary
            </h2>
            <p className="text-slate-600 leading-relaxed text-sm font-normal">
              {summary}
            </p>
          </div>

          {/* Contact Details */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3 pb-2 border-b border-slate-100">
              Candidate Profile
            </h2>
            <div className="grid grid-cols-2 gap-3 text-xs md:text-sm">
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-slate-400 flex items-center gap-1.5 mb-1 text-[11px]"><FaEnvelope /> Email</p>
                <p className="font-semibold text-slate-700 truncate">{contact.email || "N/A"}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-slate-400 flex items-center gap-1.5 mb-1 text-[11px]"><FaPhone /> Phone</p>
                <p className="font-semibold text-slate-700 truncate">{contact.phone || "N/A"}</p>
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-slate-400 flex items-center gap-1.5 mb-1 text-[11px]"><FaGithub /> GitHub</p>
                {contact.github ? (
                  <a href={contact.github} target="_blank" rel="noreferrer" className="font-semibold text-blue-600 truncate block hover:underline">{contact.github.replace(/^https?:\/\/(www\.)?/, "")}</a>
                ) : <p className="font-semibold text-slate-400">N/A</p>}
              </div>
              <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                <p className="text-slate-400 flex items-center gap-1.5 mb-1 text-[11px]"><FaLinkedin /> LinkedIn</p>
                {contact.linkedin ? (
                  <a href={contact.linkedin} target="_blank" rel="noreferrer" className="font-semibold text-blue-600 truncate block hover:underline">{contact.linkedin.replace(/^https?:\/\/(www\.)?/, "")}</a>
                ) : <p className="font-semibold text-slate-400">N/A</p>}
              </div>
            </div>
          </div>
        </div>

        {/* Career Recommendations */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
          <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
            <span className="w-1.5 h-4 bg-emerald-600 rounded-sm"></span> Alternate Career Trajectories
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {careerRecommendation.map((r, i) => (
              <div key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-200/60">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-semibold text-slate-700 text-sm truncate max-w-[75%]">{r.role}</span>
                  <span className="text-xs md:text-sm font-bold text-emerald-600">{r.confidence.toFixed(0)}%</span>
                </div>
                <div className="w-full bg-slate-200 rounded-full h-2">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: `${r.confidence}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Skills Dashboard */}
        <div className="grid md:grid-cols-2 gap-5">
          {/* Top Skills */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaRocket className="text-emerald-500" /> Core Ecosystem Strengths
            </h2>
            <div className="flex flex-wrap gap-2">
              {topSkills.map((skill, index) => (
                <span key={index} className="px-3 py-1 rounded-lg bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-100">
                  {skill}
                </span>
              ))}
            </div>
          </div>

          {/* Missing Skills */}
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaExclamationTriangle className="text-amber-500" /> Critical Skill Gaps
            </h2>
            <div className="flex flex-wrap gap-2">
              {missingSkills.length === 0 ? (
                <p className="text-sm text-slate-400 italic">No operational gaps detected.</p>
              ) : (
                missingSkills.map((skill, index) => (
                  <span key={index} className="px-3 py-1 rounded-lg bg-rose-50 text-rose-700 text-xs font-semibold border border-rose-100">
                    {skill}
                  </span>
                ))
              )}
            </div>
          </div>
        </div>

        {/* Strengths & Weaknesses */}
        <div className="grid md:grid-cols-2 gap-5">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-emerald-800 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaCheckCircle className="text-emerald-500" /> Identified Competitive Edge
            </h2>
            <div className="space-y-2.5">
              {strengths.map((item, i) => (
                <div key={i} className="bg-emerald-50/40 border border-emerald-100/80 rounded-xl p-3 text-sm text-slate-700 font-medium">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-rose-800 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaExclamationTriangle className="text-rose-500" /> Architectural Vulnerabilities
            </h2>
            <div className="space-y-2.5">
              {weaknesses.map((item, i) => (
                <div key={i} className="bg-rose-50/40 border border-rose-100/80 rounded-xl p-3 text-sm text-slate-700 font-medium">
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Suggestions & Technical Index */}
        <div className="grid md:grid-cols-2 gap-5">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaLightbulb className="text-amber-500" /> Strategic Action Items
            </h2>
            <div className="space-y-2.5">
              {suggestions.map((item, i) => (
                <div key={i} className="rounded-xl bg-amber-50/40 border border-amber-100/80 p-3 text-sm text-slate-700">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3.5 flex items-center gap-2">
              <FaLaptopCode className="text-indigo-500" /> General Tech Registry
            </h2>
            <div className="flex flex-wrap gap-2">
              {skills.map((skill, i) => (
                <span key={i} className="bg-slate-50 border border-slate-200 text-slate-600 rounded-lg px-3 py-1 text-xs font-medium">
                  {skill}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Projects Tracker */}
        <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
          <div className="flex justify-between items-center mb-4 pb-2 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
              <FaFolderOpen className="text-slate-600" /> Verified Portfolio Projects
            </h2>
            <span className="text-xs bg-slate-100 font-semibold px-3 py-1 rounded-full text-slate-500">
              {projects.length} Total
            </span>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {projects.map((project, index) => (
              <div key={index} className="rounded-xl border border-slate-100 bg-slate-50/50 hover:border-emerald-500/30 hover:bg-white transition-all p-4 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-bold text-slate-800 text-sm truncate max-w-[75%]">{project.name}</h3>
                    <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider">
                      Repo
                    </span>
                  </div>
                  <p className="text-slate-500 text-xs md:text-sm mt-2 line-clamp-3 leading-relaxed">
                    {project.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  );
}

export default ResumeReport;
