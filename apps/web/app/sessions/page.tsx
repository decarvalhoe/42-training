export const metadata = {
  title: "Sessions — 42 Training",
  description: "Manage tmux shell practice sessions",
};

export default function SessionsPage() {
  return (
    <SessionsClient />
  );
}

import SessionsClient from "./SessionsClient";
