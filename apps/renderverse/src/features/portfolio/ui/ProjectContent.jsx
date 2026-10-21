import { FaGithub } from "react-icons/fa";
import { BsBrowserChrome } from "react-icons/bs";
import PropTypes from "prop-types";

export default function ProjectContent({ content }) {
  const { proj_name, proj_desc, proj_link, github_link, proj_stack, vid_path } =
    content;
  return (
    <>
      <div style={{ display: "flex" }}>
        <h2>{proj_name}</h2>
      </div>
      <div>
        <video width={"100%"} src={vid_path} autoPlay muted loop></video>
      </div>
      <ul style={{ marginTop: "1rem", display: "flex" }}>
        {github_link && (
          <li
            style={{
              fontSize: "0.8rem",
              display: "grid",
              alignItems: "center",
              justifyContent: "center",
              background: "#1EFAD2",
              borderRadius: "20px",
              marginRight: "10px",
              boxShadow: "2px 2px 5px -2px #000",
              cursor: "pointer",
              height: "30px",
              width: "30px",
            }}
          >
            <a href={github_link} target="_blank" style={{ display: "flex" }}>
              <FaGithub size={22} style={{ textDecoration: "none" }} />
            </a>
          </li>
        )}
        {proj_link && (
          <li
            style={{
              fontSize: "0.8rem",
              display: "grid",
              alignItems: "center",
              justifyContent: "center",
              background: "#1EFAD2",
              borderRadius: "20px",
              boxShadow: "2px 2px 5px -2px #000",
              cursor: "pointer",
              height: "30px",
              width: "30px",
            }}
          >
            <a href={proj_link} target="_blank" style={{ display: "flex" }}>
              <BsBrowserChrome size={20} style={{ textDecoration: "none" }} />
            </a>
          </li>
        )}
      </ul>
      <div
        style={{
          marginTop: "1rem",
          marginBottom: "1rem",
          textAlign: "justify",
        }}
      >
        <span>{proj_desc}</span>
      </div>
      <div>
        <ul>
          {proj_stack.map((stack) => {
            return (
              <li
                key={stack}
                style={{
                  fontSize: "0.8rem",
                  display: "inline-flex",
                  alignItems: "center",
                  background: "#1EFAD2",
                  borderRadius: "5px",
                  marginRight: "10px",
                  boxShadow: "2px 2px 5px -5px #000",
                  padding: "0.5rem",
                }}
              >
                {stack}
              </li>
            );
          })}
        </ul>
      </div>
    </>
  );
}

ProjectContent.propTypes = {
  content: PropTypes.object,
};
