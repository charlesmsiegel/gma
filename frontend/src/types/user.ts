export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string;
  timezone: string;
  date_joined: string;
}

export interface LoginData {
  username: string;
  password: string;
}

export interface RegisterData {
  username: string;
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
}

export interface ProfileUpdateData {
  first_name: string;
  last_name: string;
  display_name: string;
  timezone: string;
  email: string;
}
