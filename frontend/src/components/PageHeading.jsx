import Icon from "./Icon.jsx";

export default function PageHeading({ eyebrow, title, icon = "shield", children }) {
  return <header className="page-heading">
    <p className="eyebrow page-kicker"><Icon name={icon}/>{eyebrow}</p>
    <h1>{title}</h1>
    {children && <p>{children}</p>}
  </header>;
}
