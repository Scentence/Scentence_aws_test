import "next-auth";

declare module "next-auth" {
  interface User {
    id: string;
    roleType?: string;
    userMode?: string;
  }

  interface Session {
    user: {
      id: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
      roleType?: string;
      userMode?: string;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id: string;
    roleType?: string;
    userMode?: string;
  }
}
