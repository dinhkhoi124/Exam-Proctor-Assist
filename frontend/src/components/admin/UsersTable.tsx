interface UserData {
  email: string;
  question_count: number;
}

interface UsersTableProps {
  users: UserData[];
}

export function UsersTable({ users }: UsersTableProps) {
  return (
    <div className="rounded-md border overflow-hidden">
      <table className="w-full caption-bottom text-sm border-collapse">
        <thead className="[&_tr]:border-b bg-muted/50">
          <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
            <th className="h-12 px-4 text-left align-middle font-medium text-foreground">Email</th>
            <th className="h-12 px-4 text-right align-middle font-medium text-foreground">Total Questions</th>
          </tr>
        </thead>
        <tbody className="[&_tr:last-child]:border-0 bg-card">
          {users.map((user) => (
            <tr key={user.email} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted text-card-foreground">
              <td className="p-4 align-middle font-medium">{user.email}</td>
              <td className="p-4 align-middle text-right">{user.question_count}</td>
            </tr>
          ))}
          {users.length === 0 && (
            <tr>
              <td colSpan={2} className="p-4 align-middle h-24 text-center text-muted-foreground">No users found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
