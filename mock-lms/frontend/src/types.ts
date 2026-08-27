// Mirrors app/web.py's JSON shape for /web-api/* — kept in lockstep with
// app/models.py's PlatformCourse / PlatformAssignment, not invented client-side.

export interface Identity {
  userId: string;
  role: 'STUDENT' | 'INSTRUCTOR' | 'ADMIN';
  name: string;
  email: string;
}

export interface CourseSummary {
  code: string;
  name: string;
  semester: string;
  credit: number;
  assignmentCount: number;
}

export interface Assignment {
  id: string;
  name: string;
  description: string;
  dueAt: string; // ISO date
  pointsPossible: number;
  updatedAt: string; // ISO datetime
  isPastDue: boolean;
}

export interface CourseDetail {
  code: string;
  name: string;
  semester: string;
  credit: number;
  assignments: Assignment[];
}

// Mirrors app/curriculum_api.py — kept in lockstep with app/models.py's
// Syllabus / CurriculumProgram / PrerequisiteNode.

export interface SyllabusSummary {
  syllabusId: number;
  syllabusName: string;
  courseNameEnglish: string;
  subjectCode: string;
  learningTeachingMethod: string;
  noCredit: number;
  preRequisite: string;
  decisionNo: string;
  isActive: boolean;
  sessionCount: number;
  questionCount: number;
  cloCount: number;
}

export interface SyllabusMaterial {
  no: number;
  description: string;
  author: string;
  publisher: string;
  publishedDate: string;
  edition: string;
  isbn: string;
  isMain: boolean;
  isHardCopy: boolean;
  isOnline: boolean;
  note?: string;
}

export interface SyllabusCLO {
  no: number;
  cloName: string;
  details: string;
}

export interface SyllabusSession {
  sessionNo: number;
  topic: string;
  type: string;
  lo: string;
  itu?: string;
  studentMaterials?: string;
  sDownload?: string;
  studentTasks: string;
  urls?: string;
}

export interface SyllabusQuestion {
  no: number;
  sessionNo: number;
  question: string;
}

export interface SyllabusAssessment {
  no: number;
  category: string;
  type: string;
  part: number;
  weight: number;
  completionCriteria: string;
  duration: string;
  clo: string;
  questionType?: string;
  noQuestion?: number;
  knowledgeAndSkill: string;
  gradingGuide: string;
  note?: string;
}

export interface SyllabusDetail {
  metadata: {
    syllabusId: number;
    syllabusName: string;
    courseNameEnglish: string;
    subjectCode: string;
    learningTeachingMethod: string;
    noCredit: number;
    degreeLevel: string;
    timeAllocation: string;
    preRequisite: string;
    description: string;
    studentTasks: string;
    tools: string;
    scoringScale: number;
    decisionNo: string;
    approvedDate: string;
    isActive: boolean;
    isApproved: boolean;
  };
  materials: SyllabusMaterial[];
  clos: SyllabusCLO[];
  sessions: SyllabusSession[];
  questions: SyllabusQuestion[];
  assessments: SyllabusAssessment[];
}

export type SubjectCategory = 'Foundation' | 'Core' | 'Specialized' | 'Elective' | 'Capstone' | 'Soft Skills';

export interface CurriculumSubject {
  code: string;
  name: string;
  credits: number;
  semester: number;
  category: SubjectCategory;
  prerequisite: string;
  syllabusId: number;
  isActive: boolean;
}

export interface CurriculumProgramSummary {
  code: string;
  name: string;
  totalCredits: number;
  semesterCount: number;
}

export interface CurriculumProgramDetail {
  code: string;
  name: string;
  faculty: string;
  decisionNo: string;
  effectiveYear: string;
  totalCredits: number;
  description: string;
  semesters: { semesterNo: number; title: string; subjects: CurriculumSubject[] }[];
}

export interface PrerequisiteNode {
  code: string;
  name: string;
  semester: number;
  credits: number;
  category: string;
  prerequisites: string[];
  isPrerequisiteOf: string[];
}
