# ===========================
# EDUCATION KEYWORDS
# ===========================

EDUCATION = {
    "bachelor", "master", "b.tech", "b.e", "m.tech",
    "bca", "mca", "bsc", "msc", "phd",
    "computer science",
    "information technology",
    "artificial intelligence",
    "data science",
    "software engineering",
    "electronics",
    "electrical engineering",
    "mechanical engineering",
    "civil engineering"
}


# ===========================
# EXPERIENCE KEYWORDS
# ===========================

EXPERIENCE = {
    "intern",
    "internship",
    "software engineer",
    "software developer",
    "web developer",
    "frontend developer",
    "backend developer",
    "full stack developer",
    "android developer",
    "ios developer",
    "machine learning engineer",
    "data scientist",
    "research assistant",
    "freelancer",
    "consultant",
    "teaching assistant",
    "professional experience",
    "work experience"
}


# ===========================
# ATS SECTIONS
# ===========================

SECTIONS = {
    "summary",
    "objective",
    "education",
    "experience",
    "projects",
    "skills",
    "certifications",
    "achievements",
    "leadership",
    "publications",
    "contact",
    "languages"
}


# ===========================
# ROLE SKILLS
# ===========================

ROLE_SKILLS = {

    "Frontend Developer": {
        "required": {
            "html", "css", "javascript", "react", "git"
        },
        "advanced": {
            "typescript", "redux", "next.js", "tailwind css",
            "webpack", "jest", "figma"
        }
    },

    "Backend Developer": {
        "required": {
            "java", "spring boot", "sql", "rest api", "git"
        },
        "advanced": {
            "docker", "aws", "microservices",
            "kubernetes", "redis", "mongodb"
        }
    },

    "Full Stack Developer": {
        "required": {
            "html", "css", "javascript", "react",
            "node.js", "express.js", "mongodb", "git"
        },
        "advanced": {
            "typescript", "docker", "aws",
            "next.js", "graphql", "redis", "ci/cd"
        }
    },

    "Python Developer": {
        "required": {
            "python", "flask", "sql", "git"
        },
        "advanced": {
            "django", "fastapi", "docker",
            "aws", "postgresql", "pytest",
            "redis", "celery"
        }
    },

    "Java Developer": {
        "required": {
            "java", "spring boot", "sql", "git"
        },
        "advanced": {
            "hibernate", "microservices",
            "docker", "aws", "kafka",
            "redis", "junit"
        }
    },

    "MERN Stack Developer": {
        "required": {
            "mongodb", "express.js", "react",
            "node.js", "javascript", "git"
        },
        "advanced": {
            "typescript", "redux", "docker",
            "aws", "graphql", "redis"
        }
    },

    "MEAN Stack Developer": {
        "required": {
            "mongodb", "express.js", "angular",
            "node.js", "typescript"
        },
        "advanced": {
            "docker", "aws", "redis",
            "rxjs", "graphql"
        }
    },

    "React Developer": {
        "required": {
            "react", "javascript", "html",
            "css", "git"
        },
        "advanced": {
            "typescript", "redux",
            "next.js", "tailwind css",
            "jest"
        }
    },

    "Angular Developer": {
        "required": {
            "angular", "typescript",
            "html", "css"
        },
        "advanced": {
            "rxjs", "ngrx",
            "docker", "jest"
        }
    },

    "Node.js Developer": {
        "required": {
            "node.js", "express.js",
            "javascript", "mongodb"
        },
        "advanced": {
            "docker", "aws",
            "graphql", "redis",
            "kafka"
        }
    },

    "PHP Developer": {
        "required": {
            "php", "mysql",
            "html", "css"
        },
        "advanced": {
            "laravel", "docker",
            "aws", "redis"
        }
    },

    "Android Developer": {
        "required": {
            "java", "kotlin",
            "android studio"
        },
        "advanced": {
            "firebase", "room",
            "jetpack compose",
            "retrofit"
        }
    },

    "Flutter Developer": {
        "required": {
            "flutter", "dart"
        },
        "advanced": {
            "firebase", "bloc",
            "provider", "rest api"
        }
    },

    "DevOps Engineer": {
        "required": {
            "linux", "docker",
            "git", "aws"
        },
        "advanced": {
            "kubernetes", "terraform",
            "jenkins", "ansible",
            "prometheus", "grafana"
        }
    },

    "Cloud Engineer": {
        "required": {
            "aws", "docker",
            "linux"
        },
        "advanced": {
            "terraform", "kubernetes",
            "azure", "gcp",
            "ci/cd"
        }
    },

    "Data Scientist": {
        "required": {
            "python", "pandas",
            "numpy", "sql"
        },
        "advanced": {
            "tensorflow", "pytorch",
            "machine learning",
            "deep learning",
            "statistics",
            "power bi"
        }
    },

    "Machine Learning Engineer": {
        "required": {
            "python",
            "machine learning",
            "numpy",
            "pandas"
        },
        "advanced": {
            "tensorflow",
            "pytorch",
            "opencv",
            "mlops",
            "docker",
            "aws"
        }
    },

    "AI Engineer": {
        "required": {
            "python",
            "machine learning",
            "tensorflow",
            "pytorch"
        },
        "advanced": {
            "llm",
            "langchain",
            "rag",
            "vector database",
            "huggingface",
            "docker"
        }
    },

    "Data Engineer": {
        "required": {
            "python",
            "sql",
            "etl"
        },
        "advanced": {
            "spark",
            "hadoop",
            "airflow",
            "kafka",
            "aws"
        }
    },

    "Cyber Security Engineer": {
        "required": {
            "linux",
            "networking",
            "python"
        },
        "advanced": {
            "wireshark",
            "burp suite",
            "metasploit",
            "owasp",
            "docker"
        }
    },

    "QA Engineer": {
        "required": {
            "testing",
            "selenium",
            "sql"
        },
        "advanced": {
            "cypress",
            "playwright",
            "pytest",
            "junit",
            "ci/cd"
        }
    }
}

SKILL_ALIASES = {
    "nodejs": "node.js",
    "node": "node.js",
    "mongo": "mongodb",
    "mongodb atlas": "mongodb",
    "js": "javascript",
    "ts": "typescript",
    "tf": "tensorflow",
    "sklearn": "scikit-learn",
    "rest": "rest api",
    "restful api": "rest api",
    "amazon web services": "aws",
    "google cloud": "gcp"
}

SKILL_GAP_SUGGESTIONS = {
    # ---------------- Cloud / DevOps ----------------
    "aws": "Learn AWS to deploy and manage scalable applications in the cloud.",
    "azure": "Learn Azure to expand your cloud development skills.",
    "gcp": "Gain experience with Google Cloud Platform for modern cloud deployments.",
    "docker": "Learn Docker to containerize and deploy applications efficiently.",
    "kubernetes": "Learn Kubernetes for container orchestration and scalable deployments.",
    "terraform": "Learn Terraform to automate cloud infrastructure.",
    "ci/cd": "Build CI/CD pipelines using GitHub Actions or Jenkins.",

    # ---------------- Backend ----------------
    "java": "Strengthen your Java fundamentals for backend development.",
    "spring boot": "Learn Spring Boot to build production-ready REST APIs.",
    "node.js": "Learn Node.js to build scalable backend services.",
    "express.js": "Build REST APIs using Express.js.",
    "rest api": "Develop secure REST APIs with authentication and validation.",
    "graphql": "Learn GraphQL for flexible API development.",
    "microservices": "Understand Microservices architecture for enterprise applications.",

    # ---------------- Database ----------------
    "mysql": "Gain experience designing relational databases using MySQL.",
    "postgresql": "Learn PostgreSQL for enterprise-level database systems.",
    "mongodb": "Learn MongoDB for NoSQL application development.",
    "sql": "Improve SQL skills for querying and database optimization.",
    "nosql": "Understand NoSQL databases for scalable applications.",

    # ---------------- Frontend ----------------
    "html": "Strengthen your HTML fundamentals.",
    "css": "Improve responsive UI development using CSS.",
    "javascript": "Master modern JavaScript (ES6+) concepts.",
    "typescript": "Learn TypeScript for large-scale JavaScript applications.",
    "react": "Develop modern user interfaces using React.",
    "redux": "Learn Redux or Context API for state management.",
    "tailwind css": "Learn Tailwind CSS for rapid UI development.",
    "bootstrap": "Gain experience building responsive layouts with Bootstrap.",

    # ---------------- Mobile ----------------
    "react native": "Learn React Native for cross-platform mobile development.",
    "flutter": "Learn Flutter for modern mobile app development.",

    # ---------------- Version Control ----------------
    "git": "Use Git effectively for version control and collaboration.",
    "github": "Maintain projects on GitHub to showcase your work.",
    "agile": "Understand Agile and Scrum development practices.",

    # ---------------- Data Science / AI ----------------
    "python": "Strengthen Python programming for AI and automation.",
    "numpy": "Learn NumPy for numerical computing.",
    "pandas": "Use Pandas for efficient data analysis.",
    "matplotlib": "Visualize data using Matplotlib.",
    "tensorflow": "Build deep learning models using TensorFlow.",
    "pytorch": "Learn PyTorch for modern deep learning applications.",
    "machine learning": "Understand supervised and unsupervised machine learning algorithms.",
    "deep learning": "Explore neural networks and deep learning concepts.",
    "nlp": "Learn Natural Language Processing techniques.",
    "computer vision": "Gain experience with image processing and computer vision.",

    # ---------------- Testing ----------------
    "unit testing": "Write unit tests to improve software reliability.",
    "jest": "Learn Jest for JavaScript testing.",
    "junit": "Use JUnit for Java application testing.",

    # ---------------- Security ----------------
    "jwt": "Implement JWT authentication for secure applications.",
    "oauth": "Understand OAuth 2.0 authentication.",
}



