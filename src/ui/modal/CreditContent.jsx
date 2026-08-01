import PropTypes from "prop-types";
import { FaSquareXTwitter } from "react-icons/fa6";
import { SiSketchfab } from "react-icons/si";
import { FaYoutube } from "react-icons/fa";
import { IoLogoCodepen } from "react-icons/io";
import { SiPixabay } from "react-icons/si";
export default function CreditContent() {
  return (
    <>
      <h2 style={{ color: "#000" }}>Credit to :</h2>
      <ul style={{ color: "#000" }}>
        <li style={{ display: "block", marginTop: "2rem" }}>
          <a href="https://twitter.com/ByNEET" target="_blank">
            <span>ByNEET for Shin Godzilla Model</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <FaSquareXTwitter style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a
            href="https://sketchfab.com/3d-models/shin-godzilla-rigged-d4283d3b9c514d03a254461f171b400f"
            target="_blank"
          >
            <span>Red Comet 0079 for Shin Godzilla Rig</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <SiSketchfab style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a href="https://www.youtube.com/@polygonrunway" target="_blank">
            <span>PolygonRunway for Globe</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <FaYoutube style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a href="https://codepen.io/mr_alien/pen/NWygPw" target="_blank">
            <span>Mr Alien for Redirecting Loading Screen</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <IoLogoCodepen style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a href="https://codepen.io/aaroniker/full/omvYNZ" target="_blank">
            <span>Aaron Iker for Animated Symbol Loading Screen</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <IoLogoCodepen style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a
            href="https://pixabay.com/sound-effects/search/shin%20godzilla/"
            target="_blank"
          >
            <span>SkullHuskXEN for Shin Godzilla Roar</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <SiPixabay style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
        <li style={{ paddingTop: "1.5rem", display: "block" }}>
          <a href="https://www.youtube.com/watch?v=lyeAzpx-YcY" target="_blank">
            <span>FNF Sussus Moogus Music</span>
            <div
              style={{
                display: "flex",
                marginTop: "0.2rem",
                justifyContent: "center",
              }}
            >
              <span>Follow on:</span>
              <FaYoutube style={{ marginLeft: "0.5rem" }} />
            </div>
          </a>
        </li>
      </ul>
    </>
  );
}

CreditContent.propTypes = {
  content: PropTypes.object,
};
