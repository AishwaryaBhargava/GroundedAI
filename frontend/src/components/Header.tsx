import { Link } from "react-router-dom";
import "../styles/Header.css";
import logo from "../assets/logo.svg";

export default function Header() {
  return (
    <header className="app-header">
      <Link to="/" className="header-left">
        <img src={logo} alt="GroundedAI logo" />
        <span className="app-title">GroundedAI</span>
      </Link>
    </header>
  );
}
