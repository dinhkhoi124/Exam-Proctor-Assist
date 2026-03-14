import { Header } from "@/components/Header";
import { ChatWindow } from "@/components/chat/ChatWindow";

const Index = () => {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <Header />
      <main className="flex-1">
        <ChatWindow />
      </main>
    </div>
  );
};

export default Index;
