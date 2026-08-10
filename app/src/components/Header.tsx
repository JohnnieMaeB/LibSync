import logo from "../assets/logo.png";

export function Header() {
  return (
    <header>
      <img src={logo} alt="AI Assistant Logo" className="logo" />
      <div>
        <h1>LibSync</h1>
        <p className="tagline">Your personal AI library assistant.</p>
      </div>
    </header>
  );
}
