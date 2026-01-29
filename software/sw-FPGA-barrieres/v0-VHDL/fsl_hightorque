library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

entity fsm_hightorque is
  port (
    clk       : in  STD_LOGIC;
    reset     : in  STD_LOGIC;
    step_ce   : in  STD_LOGIC;
    enable    : in  STD_LOGIC;
    direction : in  STD_LOGIC;
    phases    : out STD_LOGIC_VECTOR(3 downto 0)
  );
end entity;

architecture Behavioral of fsm_hightorque is
  type state_type is (s3, s6, s9, s12);
  signal st, st_next : state_type := s3;
begin
  process(clk, reset)
  begin
    if reset='1' then
      st <= s3;
    elsif rising_edge(clk) then
      if enable='1' and step_ce='1' then
        st <= st_next;
      end if;
    end if;
  end process;

  process(st, direction)
  begin
    case st is
      when s3  => if direction='0' then st_next <= s6;  else st_next <= s12; end if;
      when s6  => if direction='0' then st_next <= s9;  else st_next <= s3;  end if;
      when s9  => if direction='0' then st_next <= s12; else st_next <= s6;  end if;
      when s12 => if direction='0' then st_next <= s3;  else st_next <= s9;  end if;
    end case;
  end process;

  with st select
    phases <= "0011" when s3,
              "0110" when s6,
              "1100" when s9,
              "1001" when s12,
              "0000" when others;
end architecture;
