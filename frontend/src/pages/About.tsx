import { Header } from "@/components/Header";
import {
  GraduationCap,
  Users,
  Zap,
  Shield,
  MessageSquare,
  Mic,
  Image as ImageIcon,
  Clock,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    icon: MessageSquare,
    title: "Text Support",
    description: "Type your questions and get instant troubleshooting guidance",
  },
  {
    icon: ImageIcon,
    title: "Image Upload",
    description: "Share screenshots of error messages for accurate diagnosis",
  },
  {
    icon: Mic,
    title: "Voice Input",
    description: "Speak your questions when typing isn't convenient",
  },
  {
    icon: Clock,
    title: "Instant Response",
    description: "Get solutions in seconds, not minutes of waiting",
  },
];

const stakeholders = [
  {
    icon: Users,
    title: "Exam Proctors",
    description:
      "Supervise exam rooms with confidence, knowing expert support is just a message away",
  },
  {
    icon: Shield,
    title: "Exam Office (Phòng Khảo thí)",
    description:
      "Reduce direct support requests by empowering proctors with self-service solutions",
  },
  {
    icon: Zap,
    title: "IT Support Staff",
    description:
      "Focus on complex issues while common problems are resolved automatically",
  },
];

const About = () => {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />

      <main className="flex-1">
        {/* Hero Section */}
        <section className="border-b border-border bg-gradient-to-b from-primary/5 to-background">
          <div className="container px-4 py-10 sm:py-16 md:py-24">
            <div className="mx-auto max-w-3xl text-center">
              <div className="mb-6 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-primary shadow-lg">
                <GraduationCap className="h-8 w-8 text-primary-foreground" />
              </div>
              <h1 className="mb-4 text-3xl font-bold tracking-tight text-foreground sm:text-4xl md:text-5xl">
                FPT Exam Proctor Support
              </h1>
              <p className="text-base text-muted-foreground sm:text-xl">
                Intelligent chatbot assistance for final exam technical support
              </p>
            </div>
          </div>
        </section>

        {/* Problem & Solution */}
        <section className="py-10 sm:py-16">
          <div className="container px-4">
            <div className="mx-auto max-w-3xl">
              <div className="grid gap-8 md:grid-cols-2">
                {/* The Problem */}
                <Card className="border-destructive/20 bg-destructive/5">
                  <CardContent className="p-6">
                    <h2 className="mb-4 text-lg font-semibold text-destructive">
                      The Challenge
                    </h2>
                    <p className="text-sm text-foreground/80">
                      During FPT University final exams, when students face technical
                      issues on their personal laptops, proctors must manually message
                      the Exam Office or IT staff. This leads to{" "}
                      <strong>slow response times</strong>,{" "}
                      <strong>fragmented communication</strong>, and an{" "}
                      <strong>unprofessional experience</strong> during critical exam
                      moments.
                    </p>
                  </CardContent>
                </Card>

                {/* The Solution */}
                <Card className="border-primary/20 bg-primary/5">
                  <CardContent className="p-6">
                    <h2 className="mb-4 text-lg font-semibold text-primary">
                      Our Solution
                    </h2>
                    <p className="text-sm text-foreground/80">
                      A web-based chatbot powered by RAG (Retrieval-Augmented
                      Generation) technology that provides{" "}
                      <strong>instant troubleshooting guidance</strong> to proctors.
                      Handle WiFi issues, login problems, browser crashes, and more —
                      all in <strong>real-time</strong>.
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="border-t border-border bg-secondary/30 py-10 sm:py-16">
          <div className="container px-4">
            <div className="mx-auto max-w-4xl">
              <h2 className="mb-12 text-center text-2xl font-bold text-foreground">
                Multimodal Support
              </h2>
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {features.map((feature) => {
                  const Icon = feature.icon;
                  return (
                    <Card
                      key={feature.title}
                      className="border-border bg-card text-center transition-shadow hover:shadow-chat-hover"
                    >
                      <CardContent className="p-6">
                        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10">
                          <Icon className="h-6 w-6 text-primary" />
                        </div>
                        <h3 className="mb-2 font-semibold text-foreground">
                          {feature.title}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {feature.description}
                        </p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Stakeholders */}
        <section className="py-10 sm:py-16">
          <div className="container px-4">
            <div className="mx-auto max-w-4xl">
              <h2 className="mb-12 text-center text-2xl font-bold text-foreground">
                Who This Helps
              </h2>
              <div className="grid gap-6 md:grid-cols-3">
                {stakeholders.map((stakeholder) => {
                  const Icon = stakeholder.icon;
                  return (
                    <Card
                      key={stakeholder.title}
                      className="border-border bg-card transition-shadow hover:shadow-chat-hover"
                    >
                      <CardContent className="p-6">
                        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-primary">
                          <Icon className="h-6 w-6 text-primary-foreground" />
                        </div>
                        <h3 className="mb-2 font-semibold text-foreground">
                          {stakeholder.title}
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          {stakeholder.description}
                        </p>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          </div>
        </section>

        {/* Tech Stack */}
        <section className="border-t border-border bg-secondary/30 py-16">
          <div className="container px-4">
            <div className="mx-auto max-w-3xl text-center">
              <h2 className="mb-6 text-2xl font-bold text-foreground">
                Built for Scale
              </h2>
              <p className="mb-8 text-muted-foreground">
                Modern technology stack designed for reliability and easy deployment
              </p>
              <div className="flex flex-wrap justify-center gap-3">
                {["React", "TypeScript", "TailwindCSS", "RAG-Ready", "Vite"].map(
                  (tech) => (
                    <span
                      key={tech}
                      className="rounded-full bg-card border border-border px-4 py-2 text-sm font-medium text-foreground"
                    >
                      {tech}
                    </span>
                  )
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-border py-8">
          <div className="container px-4">
            <div className="flex flex-col items-center justify-between gap-4 md:flex-row">
              <div className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                  <GraduationCap className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="font-semibold text-foreground">
                  FPT Exam Support
                </span>
              </div>
              <p className="text-sm text-muted-foreground">
                © {new Date().getFullYear()} FPT University. All rights reserved.
              </p>
            </div>
          </div>
        </footer>
      </main>
    </div>
  );
};

export default About;
